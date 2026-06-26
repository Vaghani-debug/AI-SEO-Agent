"""
SEO Audit Data Models.

Pydantic models for request/response validation, type safety,
and automatic FastAPI /docs schema generation.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SEOIssue(BaseModel):
    """A single SEO issue detected during the rule-based evaluation."""
    severity: str       = Field(description="High, Medium, or Low")
    category: str       = Field(description="Issue category e.g. Technical SEO, Metadata")
    issue: str          = Field(description="Short human-readable description of the issue")
    recommendation: str = Field(description="Actionable fix guidance")


class SEOScore(BaseModel):
    """Numeric SEO health score and corresponding letter grade."""
    score: int  = Field(ge=0, le=100, description="Score from 0 (worst) to 100 (perfect)")
    grade: str  = Field(description="Letter grade: A, B, C, D, or F")


class AuditSummary(BaseModel):
    """Issue count breakdown by severity level."""
    total_issues: int = Field(ge=0)
    high: int         = Field(ge=0)
    medium: int       = Field(ge=0)
    low: int          = Field(ge=0)


class RequestInfo(BaseModel):
    """Metadata about the crawled HTTP request."""
    input_url: str
    final_url: str
    http_status: Optional[int] = None


class AIAnalysis(BaseModel):
    """AI-generated SEO analysis produced by the Gemini agent."""
    overall_assessment: str         = Field(description="Narrative SEO health summary")
    priority_ranking: list[str]     = Field(description="Issues ordered by business impact")
    detailed_recommendations: list[dict] = Field(description="Per-issue fix guidance from AI")
    content_suggestions: dict       = Field(description="AI-rewritten title and meta description")
    keyword_insights: list[str]     = Field(description="Keyword gap and content observations")


class AuditResponse(BaseModel):
    """Top-level SEO audit API response envelope."""
    success: bool
    message: str
    execution_time_seconds: Optional[float] = None
    data: Optional[dict] = None
