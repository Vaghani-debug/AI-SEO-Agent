"""
LangGraph SEO Audit Workflow.

Full node pipeline (Phase 1 — sequential):

    crawl_node
        ↓  (→ aggregate if crawl fails)
    metadata_node
        ↓
    headings_node
        ↓
    images_node
        ↓
    links_node
        ↓
    technical_node
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

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from app.services.metadata import extract_metadata
from app.services.headings import extract_headings
from app.services.images import extract_images
from app.services.links import extract_links
from app.services.technical import extract_technical
from app.evaluators.seo_evaluator import evaluate_seo
from app.evaluators.score_calculator import calculate_seo_score
from app.agents.seo_analyst import analyze_seo_with_ai
from app.utils.logger import logger


# ─────────────────────────────────────────────
# Typed Workflow State
# ─────────────────────────────────────────────

class AuditState(TypedDict):
    """
    Explicit typed state shared across every workflow node.

    Each node reads only the fields it needs and writes only
    the fields it owns — nothing else is modified.
    """

    # ── Inputs ──────────────────────────────────────────────────
    url: str                            # raw URL from API request
    enable_ai: bool                     # whether AI analysis is requested

    # ── Browser lifecycle ────────────────────────────────────────
    playwright_obj: Optional[Any]       # must be stopped in aggregate_node
    browser: Optional[Any]             # must be closed in aggregate_node

    # ── Crawl results ────────────────────────────────────────────
    page: Optional[Any]                 # live Playwright page object
    status_code: Optional[int]          # HTTP status after redirects
    final_url: Optional[str]            # URL after all redirects
    crawl_time: Optional[float]         # seconds to complete navigation
    crawl_success: bool                 # False → skip to aggregate_node
    crawl_error: Optional[str]

    # ── Extraction results (one field per extraction node) ────────
    metadata: Optional[dict]            # title, description, canonical, robots
    heading_data: Optional[dict]        # H1-H6 counts + first H1 text
    image_data: Optional[dict]          # total images, missing ALT count
    link_data: Optional[dict]           # internal + external link counts
    technical_data: Optional[dict]      # charset, viewport, lang, OG, Twitter

    # ── Validation ───────────────────────────────────────────────
    validation_passed: bool             # False → skip to aggregate_node
    validation_warnings: list           # non-fatal issues noted during validation

    # ── Evaluation ───────────────────────────────────────────────
    seo_data: Optional[dict]            # assembled dict consumed by evaluate_seo
    issues: Optional[list]              # list of SEO issue dicts

    # ── Scoring ──────────────────────────────────────────────────
    seo_score: Optional[dict]           # {"score": int, "grade": str}

    # ── AI Analysis ──────────────────────────────────────────────
    ai_analysis: Optional[dict]         # Gemini output or None

    # ── Cross-node error log ─────────────────────────────────────
    errors: list                        # non-fatal errors collected across nodes

    # ── Final response ───────────────────────────────────────────
    audit_result: Optional[dict]        # the JSON returned to the API caller


# ─────────────────────────────────────────────
# Node 1: Crawl
# ─────────────────────────────────────────────

def crawl_node(state: AuditState) -> dict:
    """
    Open browser and navigate to the target URL.

    Delegates to crawler.crawl_page() which is browser-only.
    Stores browser objects in state so aggregate_node can always
    close them regardless of what happens in later nodes.
    """

    from app.services.crawler import crawl_page

    try:
        result = crawl_page(state["url"])
        return {
            "page":           result["page"],
            "browser":        result["browser"],
            "playwright_obj": result["playwright_obj"],
            "status_code":    result["status_code"],
            "final_url":      result["final_url"],
            "crawl_time":     result["crawl_time"],
            "crawl_success":  True,
            "crawl_error":    None,
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
# Nodes 2–6: Individual Extraction Nodes
# ─────────────────────────────────────────────
# Each node owns exactly one SEO dimension.
# They fail independently — one failure does not block the others.
# Phase 2: these five nodes can run in parallel (LangGraph fan-out).

def metadata_node(state: AuditState) -> dict:
    """Extract title, meta description, canonical URL, robots tag."""
    try:
        return {"metadata": extract_metadata(state["page"])}
    except Exception as e:
        logger.error(f"metadata_node failed: {e}")
        return {"metadata": {}, "errors": state.get("errors", []) + [f"metadata: {e}"]}


def headings_node(state: AuditState) -> dict:
    """Extract H1-H6 counts and first H1 text."""
    try:
        return {"heading_data": extract_headings(state["page"])}
    except Exception as e:
        logger.error(f"headings_node failed: {e}")
        return {"heading_data": {}, "errors": state.get("errors", []) + [f"headings: {e}"]}


def images_node(state: AuditState) -> dict:
    """Extract total image count and missing ALT text count."""
    try:
        return {"image_data": extract_images(state["page"])}
    except Exception as e:
        logger.error(f"images_node failed: {e}")
        return {"image_data": {}, "errors": state.get("errors", []) + [f"images: {e}"]}


def links_node(state: AuditState) -> dict:
    """Extract internal and external link counts."""
    try:
        return {"link_data": extract_links(state["page"])}
    except Exception as e:
        logger.error(f"links_node failed: {e}")
        return {"link_data": {}, "errors": state.get("errors", []) + [f"links: {e}"]}


def technical_node(state: AuditState) -> dict:
    """Extract charset, viewport, lang attribute, OG tags, Twitter Card."""
    try:
        return {"technical_data": extract_technical(state["page"])}
    except Exception as e:
        logger.error(f"technical_node failed: {e}")
        return {"technical_data": {}, "errors": state.get("errors", []) + [f"technical: {e}"]}


# ─────────────────────────────────────────────
# Node 7: Validate
# ─────────────────────────────────────────────

def validate_node(state: AuditState) -> dict:
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

def evaluate_node(state: AuditState) -> dict:
    """
    Run rule-based SEO issue detection.

    Assembles the seo_data contract dict expected by evaluate_seo()
    and returns the raw list of issues. Scoring is a separate concern
    handled by scoring_node.
    """

    seo_data = {
        "request":      {"http_status": state["status_code"]},
        "metadata":     state.get("metadata") or {},
        "heading_data": state.get("heading_data") or {},
        "image_data":   state.get("image_data") or {},
        "link_data":    state.get("link_data") or {},
        "technical":    state.get("technical_data") or {},
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

def scoring_node(state: AuditState) -> dict:
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

def ai_analyze_node(state: AuditState) -> dict:
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

def aggregate_node(state: AuditState) -> dict:
    """
    Build the final JSON response and close all browser resources.

    This node ALWAYS runs — it is the terminal node for both the
    happy path and every failure path. Browser cleanup happens here
    so resources are never leaked regardless of which node failed.
    """

    # ── Browser cleanup (always, best-effort) ─────────────────
    try:
        if state.get("browser"):
            state["browser"].close()
        if state.get("playwright_obj"):
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
                    "metadata":  state.get("metadata"),
                    "headings":  state.get("heading_data"),
                    "images":    state.get("image_data"),
                    "links":     state.get("link_data"),
                    "technical": state.get("technical_data"),
                },
                "seo_score":    state.get("seo_score"),
                "ai_analysis":  state.get("ai_analysis"),
            }
        }
    }


# ─────────────────────────────────────────────
# Conditional Edge Routing
# ─────────────────────────────────────────────

def route_after_crawl(state: AuditState) -> str:
    """Skip extraction entirely if the browser could not reach the page."""
    return "metadata" if state.get("crawl_success") else "aggregate"


def route_after_validate(state: AuditState) -> str:
    """Skip evaluation if critical data is missing."""
    return "evaluate" if state.get("validation_passed") else "aggregate"


def route_after_scoring(state: AuditState) -> str:
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
        crawl     fails → aggregate
        validate  fails → aggregate
        ai=False         → aggregate (skip ai_analyze)

    Returns:
        Compiled StateGraph ready to invoke.
    """

    graph = StateGraph(AuditState)

    # Register all nodes
    graph.add_node("crawl",      crawl_node)
    graph.add_node("metadata",   metadata_node)
    graph.add_node("headings",   headings_node)
    graph.add_node("images",     images_node)
    graph.add_node("links",      links_node)
    graph.add_node("technical",  technical_node)
    graph.add_node("validate",   validate_node)
    graph.add_node("evaluate",   evaluate_node)
    graph.add_node("scoring",    scoring_node)
    graph.add_node("ai_analyze", ai_analyze_node)
    graph.add_node("aggregate",  aggregate_node)

    # Entry point
    graph.set_entry_point("crawl")

    # crawl → extraction chain (or → aggregate on failure)
    graph.add_conditional_edges("crawl", route_after_crawl, {
        "metadata":  "metadata",
        "aggregate": "aggregate",
    })

    # Sequential extraction chain
    graph.add_edge("metadata",  "headings")
    graph.add_edge("headings",  "images")
    graph.add_edge("images",    "links")
    graph.add_edge("links",     "technical")
    graph.add_edge("technical", "validate")

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
    All orchestration is inside the LangGraph state graph.

    Parameters:
        url (str): The website URL to audit.
        enable_ai (bool): Whether to run Gemini AI analysis.

    Returns:
        dict: Complete SEO audit response ready to return as JSON.
    """

    initial_state: AuditState = {
        "url":                url,
        "enable_ai":          enable_ai,
        "playwright_obj":     None,
        "browser":            None,
        "page":               None,
        "status_code":        None,
        "final_url":          None,
        "crawl_time":         None,
        "crawl_success":      False,
        "crawl_error":        None,
        "metadata":           None,
        "heading_data":       None,
        "image_data":         None,
        "link_data":          None,
        "technical_data":     None,
        "validation_passed":  False,
        "validation_warnings": [],
        "seo_data":           None,
        "issues":             None,
        "seo_score":          None,
        "ai_analysis":        None,
        "errors":             [],
        "audit_result":       None,
    }

    final_state = _workflow.invoke(initial_state)
    return final_state["audit_result"]


from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.services.metadata import extract_metadata
from app.services.headings import extract_headings
from app.services.images import extract_images
from app.services.links import extract_links
from app.services.technical import extract_technical
from app.evaluators.seo_evaluator import evaluate_seo
from app.evaluators.score_calculator import calculate_seo_score
from app.agents.seo_analyst import analyze_seo_with_ai
from app.utils.logger import logger


# ─────────────────────────────────────────────
# Shared State
# ─────────────────────────────────────────────

class AuditState(TypedDict):
    """State passed between every node in the workflow."""

    # ── Inputs ──────────────────────────────
    url: str
    enable_ai: bool

    # ── Browser lifecycle (not serialized — no checkpointer used) ──
    playwright_obj: Optional[object]   # must be stopped by aggregate_node
    browser: Optional[object]          # must be closed by aggregate_node

    # ── Crawl results ────────────────────────
    page: Optional[object]             # live Playwright page object
    status_code: Optional[int]
    final_url: Optional[str]
    crawl_time: Optional[float]
    crawl_success: bool
    crawl_error: Optional[str]

    # ── Extraction results ───────────────────
    metadata: Optional[dict]
    heading_data: Optional[dict]
    image_data: Optional[dict]
    link_data: Optional[dict]
    technical_data: Optional[dict]

    # ── Evaluation results ───────────────────
    seo_data: Optional[dict]           # aggregated dict passed to evaluator
    issues: Optional[list]
    seo_score: Optional[dict]

    # ── AI analysis results ──────────────────
    ai_analysis: Optional[dict]

    # ── Final response ───────────────────────
    audit_result: Optional[dict]       # the JSON returned to the API caller


# ─────────────────────────────────────────────
# Node 1: Crawl
# ─────────────────────────────────────────────

def crawl_node(state: AuditState) -> dict:
    """
    Open browser and navigate to the target URL.

    Delegates to crawler.crawl_page() which is responsible for
    browser lifecycle only. Stores browser objects in state so
    aggregate_node can close them regardless of later failures.
    """

    from app.services.crawler import crawl_page

    try:
        result = crawl_page(state["url"])

        return {
            "page":           result["page"],
            "browser":        result["browser"],
            "playwright_obj": result["playwright_obj"],
            "status_code":    result["status_code"],
            "final_url":      result["final_url"],
            "crawl_time":     result["crawl_time"],
            "crawl_success":  True,
            "crawl_error":    None,
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
# Node 2: Extract
# ─────────────────────────────────────────────

def extract_node(state: AuditState) -> dict:
    """
    Run all SEO extraction services on the live Playwright page.

    Each service is independently responsible for one SEO dimension:
        metadata   → title, description, canonical, robots
        headings   → H1-H6 counts and first H1 text
        images     → total count, missing ALT count
        links      → internal and external link counts
        technical  → charset, viewport, lang, OG tags, Twitter Card
    """

    page = state["page"]

    metadata      = extract_metadata(page)
    heading_data  = extract_headings(page)
    image_data    = extract_images(page)
    link_data     = extract_links(page)
    technical_data = extract_technical(page)

    logger.info("extract_node: all SEO data collected.")

    return {
        "metadata":       metadata,
        "heading_data":   heading_data,
        "image_data":     image_data,
        "link_data":      link_data,
        "technical_data": technical_data,
    }


# ─────────────────────────────────────────────
# Node 3: Evaluate
# ─────────────────────────────────────────────

def evaluate_node(state: AuditState) -> dict:
    """
    Run rule-based SEO evaluation and calculate the SEO score.

    Assembles the seo_data dict (the contract expected by evaluate_seo),
    runs all checks, then calculates a numeric score and letter grade.
    """

    # Build the canonical seo_data dict consumed by the evaluator
    seo_data = {
        "request":      {"http_status": state["status_code"]},
        "metadata":     state["metadata"],
        "heading_data": state["heading_data"],
        "image_data":   state["image_data"],
        "link_data":    state["link_data"],
        "technical":    state["technical_data"],
    }

    issues    = evaluate_seo(seo_data)
    seo_score = calculate_seo_score(issues)

    logger.info(f"evaluate_node: {len(issues)} issues found | score={seo_score.get('score')}")

    return {
        "seo_data":  seo_data,
        "issues":    issues,
        "seo_score": seo_score,
    }


# ─────────────────────────────────────────────
# Node 4: AI Analysis (optional)
# ─────────────────────────────────────────────

def ai_analyze_node(state: AuditState) -> dict:
    """
    Run AI-powered SEO analysis using Google Gemini.

    Only executes when enable_ai=True. If the LLM call fails,
    ai_analysis is set to None so the rest of the response is
    still returned (graceful degradation).
    """

    logger.info("ai_analyze_node: calling Gemini...")
    ai_result = analyze_seo_with_ai(state["seo_data"], state["issues"])

    return {"ai_analysis": ai_result}


# ─────────────────────────────────────────────
# Node 5: Aggregate
# ─────────────────────────────────────────────

def aggregate_node(state: AuditState) -> dict:
    """
    Build the final JSON response and close browser resources.

    This node ALWAYS runs — it is the terminal node for both the
    success path and the crawl-failure path. Browser cleanup is
    done here so resources are never leaked.
    """

    # ── Browser cleanup ──────────────────────────────────────────
    # Always close browser/playwright regardless of success/failure
    try:
        if state.get("browser"):
            state["browser"].close()
        if state.get("playwright_obj"):
            state["playwright_obj"].stop()
    except Exception:
        pass  # best-effort cleanup

    # ── Crawl failure response ───────────────────────────────────
    if not state.get("crawl_success"):
        return {
            "audit_result": {
                "success": False,
                "message": "Website could not be reached.",
                "url":     state["url"],
                "error":   state.get("crawl_error", "Unknown error"),
            }
        }

    # ── Successful audit response ────────────────────────────────
    issues = state.get("issues", [])

    high_count   = sum(1 for i in issues if i.get("severity") == "High")
    medium_count = sum(1 for i in issues if i.get("severity") == "Medium")
    low_count    = sum(1 for i in issues if i.get("severity") == "Low")

    logger.info(f"SEO Audit Complete | URL={state['url']} | Issues={len(issues)} | Score={state['seo_score'].get('score')}")

    return {
        "audit_result": {
            "success": True,
            "message": "SEO audit completed successfully.",
            "execution_time_seconds": state.get("crawl_time"),
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
                    "metadata":  state.get("metadata"),
                    "headings":  state.get("heading_data"),
                    "images":    state.get("image_data"),
                    "links":     state.get("link_data"),
                    "technical": state.get("technical_data"),
                },
                "seo_score":    state.get("seo_score"),
                "ai_analysis":  state.get("ai_analysis"),
            }
        }
    }


# ─────────────────────────────────────────────
# Conditional Edge Routing
# ─────────────────────────────────────────────

def route_after_crawl(state: AuditState) -> str:
    """Route to extract if crawl succeeded, else skip straight to aggregate."""
    return "extract" if state.get("crawl_success") else "aggregate"


def route_after_evaluate(state: AuditState) -> str:
    """Route to AI analysis if requested, else go directly to aggregate."""
    return "ai_analyze" if state.get("enable_ai") else "aggregate"


# ─────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Build and compile the LangGraph SEO audit state graph.

    Flow:
        crawl → (conditional) → extract → evaluate → (conditional) → ai_analyze → aggregate → END
                             ↘ aggregate (crawl failed)            ↘ aggregate (AI disabled)

    Returns:
        Compiled StateGraph ready to invoke.
    """

    graph = StateGraph(AuditState)

    # Register all nodes
    graph.add_node("crawl",      crawl_node)
    graph.add_node("extract",    extract_node)
    graph.add_node("evaluate",   evaluate_node)
    graph.add_node("ai_analyze", ai_analyze_node)
    graph.add_node("aggregate",  aggregate_node)

    # Entry point
    graph.set_entry_point("crawl")

    # crawl → extract or aggregate (if crawl failed)
    graph.add_conditional_edges("crawl", route_after_crawl, {
        "extract":   "extract",
        "aggregate": "aggregate",
    })

    # extract → evaluate (always)
    graph.add_edge("extract", "evaluate")

    # evaluate → ai_analyze or aggregate
    graph.add_conditional_edges("evaluate", route_after_evaluate, {
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

# Build the workflow once at module load (compiled graph is reusable)
_workflow = build_workflow()


def run_audit(url: str, enable_ai: bool = False) -> dict:
    """
    Run the full SEO audit workflow for a given URL.

    This is the single entry point called by the FastAPI endpoint.
    All orchestration happens inside the LangGraph state graph.

    Parameters:
        url (str): The website URL to audit.
        enable_ai (bool): Whether to run Gemini AI analysis.

    Returns:
        dict: Complete SEO audit response ready to return as JSON.
    """

    initial_state: AuditState = {
        "url":            url,
        "enable_ai":      enable_ai,
        "playwright_obj": None,
        "browser":        None,
        "page":           None,
        "status_code":    None,
        "final_url":      None,
        "crawl_time":     None,
        "crawl_success":  False,
        "crawl_error":    None,
        "metadata":       None,
        "heading_data":   None,
        "image_data":     None,
        "link_data":      None,
        "technical_data": None,
        "seo_data":       None,
        "issues":         None,
        "seo_score":      None,
        "ai_analysis":    None,
        "audit_result":   None,
    }

    final_state = _workflow.invoke(initial_state)
    return final_state["audit_result"]

