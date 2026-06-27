"""
Tests for the FastAPI /audit endpoint (app/main.py).

Uses FastAPI's TestClient (backed by httpx) — no real browser is launched.
The Playwright crawler is mocked to return a controlled page object,
and all extraction services are mocked to return predictable data.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# GET / — landing page
# ---------------------------------------------------------------------------

class TestHomePage:
    def test_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_html(self):
        response = client.get("/")
        assert "text/html" in response.headers["content-type"]

    def test_contains_audit_endpoint_hint(self):
        response = client.get("/")
        assert "/audit" in response.text


# ---------------------------------------------------------------------------
# GET /audit — URL validation (no browser involved)
# ---------------------------------------------------------------------------

class TestAuditUrlValidation:
    def test_rejects_blank_url(self):
        # FastAPI Query(...) raises 422 when required param is missing
        response = client.get("/audit")
        assert response.status_code == 422

    def test_rejects_obviously_invalid_url(self):
        response = client.get("/audit?url=not_a_url!!!")
        data = response.json()
        assert data["success"] is False

    def test_accepts_full_https_url(self):
        """A well-formed URL should pass validation (even if crawl later fails)."""
        with patch("app.main.run_audit", return_value={"success": False, "message": "x", "url": "https://example.com"}):
            response = client.get("/audit?url=https://example.com")
        assert response.status_code == 200

    def test_accepts_bare_domain(self):
        with patch("app.main.run_audit", return_value={"success": False, "message": "x", "url": "example.com"}):
            response = client.get("/audit?url=example.com")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /audit — successful audit (fully mocked pipeline)
# ---------------------------------------------------------------------------

_MOCK_AUDIT_RESULT = {
    "success": True,
    "message": "SEO audit completed successfully.",
    "execution_time_seconds": 1.2,
    "warnings": [],
    "errors": [],
    "data": {
        "request": {
            "input_url": "https://example.com",
            "final_url": "https://example.com/",
            "http_status": 200,
        },
        "summary": {"total_issues": 0, "high": 0, "medium": 0, "low": 0},
        "findings": [],
        "seo": {
            "metadata": {"title": "Example", "meta_description": "Desc", "canonical": "https://example.com/", "robots": None},
            "headings": {"h1_count": 1, "h1_status": "Valid", "h1": "Example"},
            "images": {"image_count": 2, "images_missing_alt": 0},
            "links": {"total_links": 5, "internal_links": 4, "external_links": 1},
            "technical": {"language": "en", "charset": "UTF-8", "viewport": "width=device-width", "favicon": None,
                          "og_title": "T", "og_description": "D", "og_image": "I", "twitter_card": "summary"},
        },
        "seo_score": {"score": 100, "grade": "A"},
        "ai_analysis": None,
    },
}


class TestAuditSuccess:
    def test_successful_audit_structure(self):
        with patch("app.main.run_audit", return_value=_MOCK_AUDIT_RESULT):
            response = client.get("/audit?url=https://example.com")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["seo_score"]["score"] == 100
        assert data["data"]["seo_score"]["grade"] == "A"

    def test_ai_disabled_by_default(self):
        """run_audit must be called with enable_ai=False when ai param is omitted."""
        captured = {}

        def _fake_run_audit(url, enable_ai=False):
            captured["enable_ai"] = enable_ai
            return _MOCK_AUDIT_RESULT

        with patch("app.main.run_audit", side_effect=_fake_run_audit):
            client.get("/audit?url=https://example.com")

        assert captured["enable_ai"] is False

    def test_ai_enabled_when_requested(self):
        captured = {}

        def _fake_run_audit(url, enable_ai=False):
            captured["enable_ai"] = enable_ai
            return _MOCK_AUDIT_RESULT

        with patch("app.main.run_audit", side_effect=_fake_run_audit):
            client.get("/audit?url=https://example.com&ai=true")

        assert captured["enable_ai"] is True

    def test_response_is_pretty_json(self):
        """PrettyJSONResponse must indent the output (2 spaces)."""
        with patch("app.main.run_audit", return_value=_MOCK_AUDIT_RESULT):
            response = client.get("/audit?url=https://example.com")
        # Indented JSON contains newlines
        assert "\n" in response.text
