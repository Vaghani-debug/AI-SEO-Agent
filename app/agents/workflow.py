"""
LangGraph SEO Audit Workflow.

This module owns ALL orchestration. The execution order is:

    crawl_node → extract_node → evaluate_node → ai_analyze_node → aggregate_node
                     ↑ conditional: skip to aggregate if crawl failed
                                                      ↑ conditional: skip if ai disabled

Node responsibilities:
    crawl_node      — opens browser, navigates (delegates to crawler.crawl_page)
    extract_node    — runs all SEO extraction services on the live page
    evaluate_node   — rule-based evaluation + SEO score calculation
    ai_analyze_node — optional Gemini AI analysis
    aggregate_node  — builds the final JSON response dict, closes browser

crawler.py is intentionally kept thin: it only opens a browser and returns a page.
"""

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

