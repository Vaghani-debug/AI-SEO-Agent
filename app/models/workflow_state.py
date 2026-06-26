"""
LangGraph Workflow State Contract.

Defines WorkflowState — the single typed dictionary passed between
every node in the SEO audit pipeline. Having the state in models/
keeps it separate from orchestration logic and makes it importable
by any module that needs to read or annotate state fields.

Lifecycle of each field group:
    Inputs         set by run_audit() before the graph starts
    Browser        set by crawl_node; released by aggregate_node
    Crawl          set by crawl_node
    Extraction     each set by its dedicated extraction node
    Validation     set by validate_node
    Evaluation     set by evaluate_node
    Scoring        set by scoring_node
    AI Analysis    set by ai_analyze_node (only when enable_ai=True)
    Errors         appended to by any node that catches a soft failure
    Result         set once by aggregate_node; read by run_audit()
"""

from typing import TypedDict, Optional, Any


class WorkflowState(TypedDict):
    """
    Explicit typed state shared across every LangGraph workflow node.

    Each node reads only the fields it needs and writes only the
    fields it owns — no other fields are modified. This contract
    eliminates accidental key overwrites and enables IDE autocomplete
    and static type checking on state access.
    """

    # ── Inputs ───────────────────────────────────────────────────────────────
    url: str                        # raw URL passed in from the API request
    enable_ai: bool                 # True → run Gemini AI analysis node

    # ── Browser lifecycle ────────────────────────────────────────────────────
    # Playwright objects are NOT serialisable; the graph must be compiled
    # without a checkpointer. aggregate_node is always responsible for cleanup.
    playwright_obj: Optional[Any]   # top-level Playwright instance → pw.stop()
    browser: Optional[Any]          # Chromium browser instance → browser.close()

    # ── Crawl results ────────────────────────────────────────────────────────
    page: Optional[Any]             # live Playwright Page (used by extraction nodes)
    status_code: Optional[int]      # final HTTP status code after redirects
    final_url: Optional[str]        # landing URL after all redirects
    crawl_time: Optional[float]     # wall-clock seconds to complete navigation
    crawl_success: bool             # False routes directly to aggregate_node
    crawl_error: Optional[str]      # exception message if crawl failed

    # ── Extraction results (one field per dedicated extraction node) ──────────
    metadata: Optional[dict]        # title, meta_description, canonical, robots
    heading_data: Optional[dict]    # h1..h6 counts + first H1 text
    image_data: Optional[dict]      # image_count, images_missing_alt
    link_data: Optional[dict]       # total_links, internal_links, external_links
    technical_data: Optional[dict]  # charset, viewport, lang, OG tags, Twitter Card

    # ── Validation ───────────────────────────────────────────────────────────
    validation_passed: bool         # False routes directly to aggregate_node
    validation_warnings: list       # non-fatal warnings collected by validate_node

    # ── Evaluation ───────────────────────────────────────────────────────────
    seo_data: Optional[dict]        # merged dict consumed by evaluate_seo()
    issues: Optional[list]          # list[dict] — one entry per detected issue

    # ── Scoring ──────────────────────────────────────────────────────────────
    seo_score: Optional[dict]       # {"score": int, "grade": str}

    # ── AI Analysis ──────────────────────────────────────────────────────────
    ai_analysis: Optional[dict]     # Gemini output dict, or None when AI is off

    # ── Cross-node error log ─────────────────────────────────────────────────
    errors: list                    # soft errors appended by individual nodes

    # ── Final response ───────────────────────────────────────────────────────
    audit_result: Optional[dict]    # fully assembled JSON returned to the caller
