"""
Tests for the LangGraph workflow routing logic (workflow.py).

Covers conditional edge routing functions and the run_audit() entry point
under crawl-failure and validation-failure conditions.
All tests use mocks — no real browser or LLM is called.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.agents.workflow import (
    route_after_crawl,
    route_after_validate,
    route_after_scoring,
)


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

class TestRouteAfterCrawl:
    def test_routes_to_metadata_on_success(self):
        state = {"crawl_success": True}
        assert route_after_crawl(state) == "metadata"

    def test_routes_to_aggregate_on_failure(self):
        state = {"crawl_success": False}
        assert route_after_crawl(state) == "aggregate"

    def test_missing_key_treated_as_failure(self):
        assert route_after_crawl({}) == "aggregate"


class TestRouteAfterValidate:
    def test_routes_to_evaluate_when_passed(self):
        state = {"validation_passed": True}
        assert route_after_validate(state) == "evaluate"

    def test_routes_to_aggregate_when_failed(self):
        state = {"validation_passed": False}
        assert route_after_validate(state) == "aggregate"


class TestRouteAfterScoring:
    def test_routes_to_ai_when_enabled(self):
        state = {"enable_ai": True}
        assert route_after_scoring(state) == "ai_analyze"

    def test_routes_to_aggregate_when_disabled(self):
        state = {"enable_ai": False}
        assert route_after_scoring(state) == "aggregate"

    def test_routes_to_aggregate_when_ai_key_absent(self):
        assert route_after_scoring({}) == "aggregate"


# ---------------------------------------------------------------------------
# run_audit — crawl failure path
# ---------------------------------------------------------------------------

class TestRunAuditCrawlFailure:
    def test_returns_failure_response_on_crawl_error(self):
        """When crawl_page raises, run_audit must return a structured failure dict."""
        with patch("app.services.crawler.crawl_page", side_effect=Exception("connect timeout")):
            from app.agents.workflow import run_audit
            result = run_audit("https://unreachable.invalid")

        assert result["success"] is False
        assert "url" in result
        # error key should surface the exception message
        assert result.get("error") or result.get("message")


# ---------------------------------------------------------------------------
# run_audit — validation failure path
# ---------------------------------------------------------------------------

class TestRunAuditValidationFailure:
    def test_returns_failure_on_empty_page_data(self):
        """
        When the page loads but returns no metadata or heading data,
        validation_passed is False and run_audit returns a failure dict.
        """
        fake_crawl = {
            "page": MagicMock(),
            "browser": MagicMock(),
            "playwright_obj": MagicMock(),
            "status_code": 200,
            "final_url": "https://example.com/",
            "crawl_time": 1.0,
        }

        with patch("app.services.crawler.crawl_page", return_value=fake_crawl), \
             patch("app.services.metadata.extract_metadata", return_value={}), \
             patch("app.services.headings.extract_headings", return_value={}):
            from app.agents.workflow import run_audit
            # reload to force re-compilation with patches active is NOT needed here
            # because the patches replace module-level functions the nodes call
            result = run_audit("https://example.com/")

        assert result["success"] is False
