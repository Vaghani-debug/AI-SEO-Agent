"""
LangGraph SEO Audit Workflow.

Defines the state graph that orchestrates the multi-agent
SEO audit pipeline: Crawl → Evaluate → AI Analyze → Aggregate.

This module provides a structured workflow that can be extended
with additional agent nodes in the future (competitor analysis,
content optimization, report generation, etc.).
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


class AuditState(TypedDict):
    """Shared state passed between all workflow nodes."""

    # Input
    url: str
    enable_ai: bool

    # Crawl results
    page: Optional[object]
    status_code: Optional[int]
    final_url: Optional[str]
    crawl_time: Optional[float]
    crawl_success: bool

    # Extraction results
    metadata: Optional[dict]
    heading_data: Optional[dict]
    image_data: Optional[dict]
    link_data: Optional[dict]
    technical_data: Optional[dict]

    # Evaluation results
    seo_data: Optional[dict]
    issues: Optional[list]
    seo_score: Optional[dict]

    # AI Analysis results
    ai_analysis: Optional[dict]


def extract_node(state: AuditState) -> dict:
    """
    Node 1: Extract all SEO data from the page.

    Runs all extraction services on the Playwright page object.
    The page must already be loaded by the crawler before this runs.
    """

    page = state["page"]

    # Run all extraction services
    metadata = extract_metadata(page)
    heading_data = extract_headings(page)
    image_data = extract_images(page)
    link_data = extract_links(page)
    technical_data = extract_technical(page)

    logger.info("Extraction node completed — all SEO data collected.")

    return {
        "metadata": metadata,
        "heading_data": heading_data,
        "image_data": image_data,
        "link_data": link_data,
        "technical_data": technical_data,
    }


def evaluate_node(state: AuditState) -> dict:
    """
    Node 2: Evaluate extracted data using rule-based SEO checks.

    Produces a list of issues and a calculated score.
    """

    # Build seo_data dict matching what evaluate_seo expects
    seo_data = {
        "request": {"http_status": state["status_code"]},
        "metadata": state["metadata"],
        "heading_data": state["heading_data"],
        "image_data": state["image_data"],
        "link_data": state["link_data"],
        "technical": state["technical_data"],
    }

    # Run rule-based evaluation
    issues = evaluate_seo(seo_data)

    # Calculate SEO score from issues
    seo_score = calculate_seo_score(issues)

    logger.info(f"Evaluate node completed — {len(issues)} issues found, score: {seo_score.get('score', 'N/A')}")

    return {
        "seo_data": seo_data,
        "issues": issues,
        "seo_score": seo_score,
    }


def ai_analyze_node(state: AuditState) -> dict:
    """
    Node 3: AI-powered analysis using Ollama LLM.

    Only runs when enable_ai=True. Provides intelligent
    recommendations beyond what rules can detect.
    """

    if not state.get("enable_ai"):
        return {"ai_analysis": None}

    logger.info("AI analysis node starting...")
    ai_result = analyze_seo_with_ai(state["seo_data"], state["issues"])

    return {"ai_analysis": ai_result}


def should_run_ai(state: AuditState) -> str:
    """
    Conditional edge: decide whether to run AI analysis.

    Skips AI node if crawl failed or AI is disabled.
    """

    if not state.get("crawl_success", False):
        return "skip"
    if not state.get("enable_ai", False):
        return "skip"
    return "analyze"


def build_workflow() -> StateGraph:
    """
    Build and compile the LangGraph workflow for SEO audit.

    Graph structure:
        extract → evaluate → (conditional) → ai_analyze → END
                                           ↘ END (if AI skipped)

    Returns:
        Compiled StateGraph ready to invoke.
    """

    # Create the state graph
    workflow = StateGraph(AuditState)

    # Add nodes
    workflow.add_node("extract", extract_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("ai_analyze", ai_analyze_node)

    # Define edges: linear flow with conditional AI
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "evaluate")

    # After evaluate, conditionally run AI or skip to end
    workflow.add_conditional_edges(
        "evaluate",
        should_run_ai,
        {
            "analyze": "ai_analyze",
            "skip": END,
        }
    )
    workflow.add_edge("ai_analyze", END)

    # Compile and return the executable graph
    return workflow.compile()
