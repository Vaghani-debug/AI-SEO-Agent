"""
Data Models for SEO Audit.

Pydantic models for request/response validation,
type safety, and automatic API documentation.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SEOIssue(BaseModel):
    """A single SEO issue detected during audit."""

    severity: str = Field(description="Issue severity: High, Medium, or Low")
    category: str = Field(description="Issue category (e.g., Technical SEO, Metadata)")
    issue: str = Field(description="Short description of the issue")
    recommendation: str = Field(description="How to fix the issue")


class SEOScore(BaseModel):
    """Calculated SEO score and grade."""

    score: int = Field(ge=0, le=100, description="Numeric score 0-100")
    grade: str = Field(description="Letter grade: A, B, C, D, or F")


class AuditSummary(BaseModel):
    """Summary counts of issues by severity."""

    total_issues: int = Field(ge=0)
    high: int = Field(ge=0)
    medium: int = Field(ge=0)
    low: int = Field(ge=0)


class RequestInfo(BaseModel):
    """Information about the crawled request."""

    input_url: str
    final_url: str
    http_status: Optional[int] = None


class AIAnalysis(BaseModel):
    """AI-generated SEO analysis from Ollama LLM."""

    overall_assessment: str = Field(description="Narrative summary of SEO health")
    priority_ranking: list[str] = Field(description="Issues ranked by business impact")
    detailed_recommendations: list[dict] = Field(description="AI-written fix guidance per issue")
    content_suggestions: dict = Field(description="Title/description rewrite suggestions")
    keyword_insights: list[str] = Field(description="Keyword observations from content")


class AuditResponse(BaseModel):
    """Full SEO audit response."""

    success: bool
    message: str
    execution_time_seconds: Optional[float] = None
    data: Optional[dict] = None
