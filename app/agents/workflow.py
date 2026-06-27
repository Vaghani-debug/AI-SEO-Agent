"""
LangGraph SEO Audit Workflow.

Full node pipeline (Phase 1 — sequential):

    crawl_node
        ↓  (→ aggregate if crawl fails)
    metadata_node  →  headings_node  →  images_node  →  links_node  →  technical_node
        ↓
    validate_node          ← guards against incomplete/invalid data
        ↓  (→ aggregate if critical data missing)
    evaluate_node          ← rule-based SEO issue detection
        ↓
    scoring_node           ← numeric score + letter grade
        ↓
    ai_analyze_node        ← optional Gemini analysis
        ↓
    aggregate_node         ← ALWAYS runs: builds JSON + closes browser

Phase 2 (future): metadata/headings/images/links/technical can run in
parallel via LangGraph fan-out, merging into a single validate_node.
"""

from langgraph.graph import StateGraph, END

from app.config import settings
from app.models.workflow_state import WorkflowState
from app.services.metadata import extract_metadata
from app.services.headings import extract_headings
from app.services.images import extract_images
from app.services.links import extract_links
from app.services.technical import extract_technical
from app.evaluators.seo_evaluator import evaluate_seo
from app.evaluators.score_calculator import calculate_seo_score
from app.agents.seo_analyst import analyze_seo_with_ai
from app.utils.cache import AuditCache
from app.utils.logger import logger

# Module-level cache — shared across all requests in this process
_cache = AuditCache(ttl_seconds=settings.AUDIT_CACHE_TTL_SECONDS)


# ─────────────────────────────────────────────
# Node 1: Crawl
# ─────────────────────────────────────────────

def crawl_node(state: WorkflowState) -> dict:
    """
    Open browser and navigate to the target URL.

    Delegates to crawler.crawl_page() which handles browser lifecycle only.
    Browser objects are stored in state so aggregate_node can always
    close them regardless of what happens in later nodes.
    """
    from app.services.crawler import crawl_page

    try:
        result = crawl_page(state["url"])
        return {
            "page":             result["page"],
            "browser":          result["browser"],
            "playwright_obj":   result["playwright_obj"],
            "status_code":      result["status_code"],
            "response_headers": result["response_headers"],
            "final_url":        result["final_url"],
            "crawl_time":       result["crawl_time"],
            "crawl_success":    True,
            "crawl_error":      None,
        }
    except Exception as e:
        logger.error(f"crawl_node failed: {e}")
        return {
            "page":           None,
            "browser":        None,
            "playwright_obj": None,
            "status_code":    None,
            "final_url":      state["url"],
            "crawl_time":     None,
            "crawl_success":  False,
            "crawl_error":    str(e),
        }


# ─────────────────────────────────────────────
# Nodes 2-6: Individual Extraction Nodes
# ─────────────────────────────────────────────
# Each node owns exactly one SEO dimension.
# They fail independently — one failure does not block the others.
# Phase 2: these five nodes can run in parallel (LangGraph fan-out).

def metadata_node(state: WorkflowState) -> dict:
    """Extract title, meta description, canonical URL, robots tag."""
    try:
        return {"metadata": extract_metadata(state["page"])}
    except Exception as e:
        logger.error(f"metadata_node failed: {e}")
        return {"metadata": {}, "errors": state.get("errors", []) + [f"metadata: {e}"]}


def headings_node(state: WorkflowState) -> dict:
    """Extract H1-H6 counts and first H1 text."""
    try:
        return {"heading_data": extract_headings(state["page"])}
    except Exception as e:
        logger.error(f"headings_node failed: {e}")
        return {"heading_data": {}, "errors": state.get("errors", []) + [f"headings: {e}"]}


def images_node(state: WorkflowState) -> dict:
    """Extract total image count and missing ALT text count."""
    try:
        return {"image_data": extract_images(state["page"])}
    except Exception as e:
        logger.error(f"images_node failed: {e}")
        return {"image_data": {}, "errors": state.get("errors", []) + [f"images: {e}"]}


def links_node(state: WorkflowState) -> dict:
    """Extract internal and external link counts."""
    try:
        return {"link_data": extract_links(state["page"])}
    except Exception as e:
        logger.error(f"links_node failed: {e}")
        return {"link_data": {}, "errors": state.get("errors", []) + [f"links: {e}"]}


def technical_node(state: WorkflowState) -> dict:
    """Extract charset, viewport, lang attribute, OG tags, Twitter Card."""
    try:
        return {"technical_data": extract_technical(state["page"])}
    except Exception as e:
        logger.error(f"technical_node failed: {e}")
        return {"technical_data": {}, "errors": state.get("errors", []) + [f"technical: {e}"]}


def structured_data_node(state: WorkflowState) -> dict:
    """Extract JSON-LD structured data blocks from the page."""
    try:
        from app.services.structured_data import extract_structured_data
        return {"structured_data": extract_structured_data(state["page"])}
    except Exception as e:
        logger.error(f"structured_data_node failed: {e}")
        return {"structured_data": {}, "errors": state.get("errors", []) + [f"structured_data: {e}"]}


def robots_node(state: WorkflowState) -> dict:
    """Fetch robots.txt and check sitemap accessibility."""
    try:
        from app.services.robots_sitemap import fetch_robots_data
        url = state.get("final_url") or state["url"]
        return {"robots_data": fetch_robots_data(url)}
    except Exception as e:
        logger.error(f"robots_node failed: {e}")
        return {"robots_data": {}, "errors": state.get("errors", []) + [f"robots: {e}"]}


def security_node(state: WorkflowState) -> dict:
    """Analyse HTTP response headers for security signals."""
    try:
        from app.services.security import extract_security_data
        result = extract_security_data(
            state.get("response_headers") or {},
            state.get("final_url") or state["url"],
        )
        return {"security_data": result}
    except Exception as e:
        logger.error(f"security_node failed: {e}")
        return {"security_data": {}, "errors": state.get("errors", []) + [f"security: {e}"]}


# ─────────────────────────────────────────────
# Node 7: Validate
# ─────────────────────────────────────────────

def validate_node(state: WorkflowState) -> dict:
    """
    Guard node — checks data quality before evaluation begins.

    Collects non-fatal warnings (soft failures) into validation_warnings.
    Sets validation_passed=False only if critical data is missing and
    evaluation would be meaningless.

    Checks:
        - HTTP status is known and not a server error (4xx/5xx)
        - Page was not redirected to a completely different domain
        - Metadata and headings returned data (minimum to evaluate)
        - Title is not unexpectedly empty
    """
    from urllib.parse import urlparse

    warnings = list(state.get("validation_warnings", []))

    # ── HTTP status check ─────────────────────────────────────
    if state.get("status_code") is None:
        warnings.append("HTTP status could not be determined")
    elif state["status_code"] >= 400:
        warnings.append(
            f"Page returned HTTP {state['status_code']} — SEO evaluation may be unreliable"
        )

    # ── Redirect domain check ─────────────────────────────────
    try:
        input_domain = urlparse(state["url"]).netloc.lstrip("www.")
        final_domain = urlparse(state.get("final_url", "")).netloc.lstrip("www.")
        if input_domain and final_domain and input_domain != final_domain:
            warnings.append(f"Redirected to different domain: {final_domain}")
    except Exception:
        pass

    # ── Metadata quality checks ───────────────────────────────
    meta = state.get("metadata") or {}
    if not meta:
        warnings.append("Metadata extraction returned empty")
    elif not meta.get("title"):
        warnings.append("Page title is missing or unexpectedly empty")

    # ── Heading data check ────────────────────────────────────
    if not state.get("heading_data"):
        warnings.append("Heading extraction returned empty")

    # ── Critical check: do we have minimum data to evaluate? ──
    has_minimum_data = bool(state.get("metadata")) and bool(state.get("heading_data"))

    if warnings:
        logger.warning(f"validate_node warnings ({len(warnings)}): {warnings}")

    return {
        "validation_passed":   has_minimum_data,
        "validation_warnings": warnings,
    }


# ─────────────────────────────────────────────
# Node 8: Evaluate
# ─────────────────────────────────────────────

def evaluate_node(state: WorkflowState) -> dict:
    """
    Run rule-based SEO issue detection.

    Assembles the seo_data contract dict expected by evaluate_seo()
    and returns the raw list of issues. Scoring is a separate concern
    handled by scoring_node.
    """
    seo_data = {
        "request":         {"http_status": state["status_code"]},
        "metadata":        state.get("metadata") or {},
        "heading_data":    state.get("heading_data") or {},
        "image_data":      state.get("image_data") or {},
        "link_data":       state.get("link_data") or {},
        "technical":       state.get("technical_data") or {},
        "structured_data": state.get("structured_data") or {},
        "robots_data":     state.get("robots_data") or {},
        "security":        state.get("security_data") or {},
    }

    issues = evaluate_seo(seo_data)
    logger.info(f"evaluate_node: {len(issues)} issues detected.")

    return {
        "seo_data": seo_data,
        "issues":   issues,
    }


# ─────────────────────────────────────────────
# Node 9: Score
# ─────────────────────────────────────────────

def scoring_node(state: WorkflowState) -> dict:
    """
    Calculate the numeric SEO score and letter grade.

    Separated from evaluate_node so scoring logic can be
    changed or extended independently (e.g. weighted scoring,
    industry benchmarks) without touching issue detection.
    """
    seo_score = calculate_seo_score(state["issues"])
    logger.info(f"scoring_node: score={seo_score.get('score')}, grade={seo_score.get('grade')}")
    return {"seo_score": seo_score}


# ─────────────────────────────────────────────
# Node 10: AI Analysis (optional)
# ─────────────────────────────────────────────

def ai_analyze_node(state: WorkflowState) -> dict:
    """
    Run AI-powered SEO analysis using Google Gemini.

    Only executes when enable_ai=True. Falls back to None
    gracefully if the LLM is unavailable.
    """
    logger.info("ai_analyze_node: calling Gemini...")
    ai_result = analyze_seo_with_ai(state["seo_data"], state["issues"])
    return {"ai_analysis": ai_result}


# ─────────────────────────────────────────────
# Node 11: Aggregate (terminal — always runs)
# ─────────────────────────────────────────────

def aggregate_node(state: WorkflowState) -> dict:
    """
    Build the final JSON response and close all browser resources.

    This node ALWAYS runs — it is the terminal node for both the
    happy path and every failure path. Browser cleanup happens here
    so resources are never leaked regardless of which node failed.
    """

    # ── Browser cleanup (always, best-effort) ─────────────────
    # Separate try/except blocks ensure playwright_obj.stop() is
    # always attempted even if browser.close() raises.
    if state.get("browser"):
        try:
            state["browser"].close()
        except Exception:
            pass
    if state.get("playwright_obj"):
        try:
            state["playwright_obj"].stop()
        except Exception:
            pass

    # ── Crawl failure response ────────────────────────────────
    if not state.get("crawl_success"):
        return {
            "audit_result": {
                "success": False,
                "message": "Website could not be reached.",
                "url":     state["url"],
                "error":   state.get("crawl_error", "Unknown error"),
            }
        }

    # ── Validation failure response ───────────────────────────
    if not state.get("validation_passed"):
        return {
            "audit_result": {
                "success": False,
                "message": "Insufficient data returned by the page to run an SEO audit.",
                "url":     state["url"],
                "warnings": state.get("validation_warnings", []),
            }
        }

    # ── Full audit response ───────────────────────────────────
    issues = state.get("issues", [])

    high_count   = sum(1 for i in issues if i.get("severity") == "High")
    medium_count = sum(1 for i in issues if i.get("severity") == "Medium")
    low_count    = sum(1 for i in issues if i.get("severity") == "Low")

    logger.info(
        f"SEO Audit Complete | URL={state['url']} | "
        f"Issues={len(issues)} | Score={state.get('seo_score', {}).get('score')}"
    )

    return {
        "audit_result": {
            "success": True,
            "message": "SEO audit completed successfully.",
            "execution_time_seconds": state.get("crawl_time"),
            "warnings": state.get("validation_warnings", []),
            "errors":   state.get("errors", []),
            "data": {
                "request": {
                    "input_url":   state["url"],
                    "final_url":   state.get("final_url"),
                    "http_status": state.get("status_code"),
                },
                "summary": {
                    "total_issues": len(issues),
                    "high":         high_count,
                    "medium":       medium_count,
                    "low":          low_count,
                },
                "findings":    issues,
                "seo": {
                    "metadata":        state.get("metadata"),
                    "headings":        state.get("heading_data"),
                    "images":          state.get("image_data"),
                    "links":           state.get("link_data"),
                    "technical":       state.get("technical_data"),
                    "structured_data": state.get("structured_data"),
                    "robots":          state.get("robots_data"),
                    "security":        state.get("security_data"),
                },
                "seo_score":    state.get("seo_score"),
                "ai_analysis":  state.get("ai_analysis"),
            },
        }
    }


# ─────────────────────────────────────────────
# Conditional Edge Routing
# ─────────────────────────────────────────────

def route_after_crawl(state: WorkflowState) -> str:
    """Skip extraction entirely if the browser could not reach the page."""
    return "metadata" if state.get("crawl_success") else "aggregate"


def route_after_validate(state: WorkflowState) -> str:
    """Skip evaluation if critical data is missing."""
    return "evaluate" if state.get("validation_passed") else "aggregate"


def route_after_scoring(state: WorkflowState) -> str:
    """Run AI analysis only when explicitly requested."""
    return "ai_analyze" if state.get("enable_ai") else "aggregate"


# ─────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Build and compile the full LangGraph SEO audit state graph.

    Sequential Phase 1 flow:
        crawl → metadata → headings → images → links → technical
              → validate → evaluate → scoring → ai_analyze → aggregate → END

    With conditional shortcuts:
        crawl     fails  → aggregate
        validate  fails  → aggregate
        ai=False         → aggregate (skip ai_analyze)

    Returns:
        Compiled StateGraph ready to invoke.
    """
    graph = StateGraph(WorkflowState)

    # Register all nodes
    graph.add_node("crawl",           crawl_node)
    graph.add_node("metadata",        metadata_node)
    graph.add_node("headings",        headings_node)
    graph.add_node("images",          images_node)
    graph.add_node("links",           links_node)
    graph.add_node("technical",       technical_node)
    graph.add_node("structured_data", structured_data_node)
    graph.add_node("robots",          robots_node)
    graph.add_node("security",        security_node)
    graph.add_node("validate",        validate_node)
    graph.add_node("evaluate",        evaluate_node)
    graph.add_node("scoring",         scoring_node)
    graph.add_node("ai_analyze",      ai_analyze_node)
    graph.add_node("aggregate",       aggregate_node)

    # Entry point
    graph.set_entry_point("crawl")

    # crawl → extraction chain (or → aggregate on failure)
    graph.add_conditional_edges("crawl", route_after_crawl, {
        "metadata":  "metadata",
        "aggregate": "aggregate",
    })

    # Sequential extraction chain
    graph.add_edge("metadata",        "headings")
    graph.add_edge("headings",        "images")
    graph.add_edge("images",          "links")
    graph.add_edge("links",           "technical")
    graph.add_edge("technical",       "structured_data")
    graph.add_edge("structured_data", "robots")
    graph.add_edge("robots",          "security")
    graph.add_edge("security",        "validate")

    # validate → evaluate (or → aggregate on critical failure)
    graph.add_conditional_edges("validate", route_after_validate, {
        "evaluate":  "evaluate",
        "aggregate": "aggregate",
    })

    # evaluate → scoring (always)
    graph.add_edge("evaluate", "scoring")

    # scoring → ai_analyze or aggregate
    graph.add_conditional_edges("scoring", route_after_scoring, {
        "ai_analyze": "ai_analyze",
        "aggregate":  "aggregate",
    })

    # ai_analyze → aggregate (always)
    graph.add_edge("ai_analyze", "aggregate")

    # aggregate → END (always)
    graph.add_edge("aggregate", END)

    return graph.compile()


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

# Compile the graph once at module load — the compiled graph is reusable
_workflow = build_workflow()


def run_audit(url: str, enable_ai: bool = False) -> dict:
    """
    Run the full SEO audit workflow for a given URL.

    Single entry point called by the FastAPI endpoint.
    Results are cached in memory for AUDIT_CACHE_TTL_SECONDS seconds
    (per URL + enable_ai combination) to avoid redundant crawls.

    Parameters:
        url (str): The website URL to audit.
        enable_ai (bool): Whether to run Gemini AI analysis.

    Returns:
        dict: Complete SEO audit response ready to return as JSON.
    """
    # ── Cache lookup ──────────────────────────────────────────
    if settings.AUDIT_CACHE_ENABLED:
        cached = _cache.get(url, enable_ai)
        if cached is not None:
            logger.info(f"Cache hit | URL={url}")
            return cached

    initial_state: WorkflowState = {
        "url":                 url,
        "enable_ai":           enable_ai,
        "playwright_obj":      None,
        "browser":             None,
        "page":                None,
        "status_code":         None,
        "final_url":           None,
        "crawl_time":          None,
        "crawl_success":       False,
        "crawl_error":         None,
        "metadata":            None,
        "heading_data":        None,
        "image_data":          None,
        "link_data":           None,
        "technical_data":      None,
        "structured_data":     None,
        "robots_data":         None,
        "security_data":       None,
        "response_headers":    {},
        "validation_passed":   False,
        "validation_warnings": [],
        "seo_data":            None,
        "issues":              None,
        "seo_score":           None,
        "ai_analysis":         None,
        "errors":              [],
        "audit_result":        None,
    }

    final_state = _workflow.invoke(initial_state)
    result = final_state["audit_result"]

    # ── Cache store (successful audits only) ──────────────────
    if result and result.get("success") and settings.AUDIT_CACHE_ENABLED:
        _cache.set(url, enable_ai, result)

    return result
