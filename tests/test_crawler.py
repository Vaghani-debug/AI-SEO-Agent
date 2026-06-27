"""
Tests for app/services/crawler.py

Covers: successful crawl, header capture, timeout retry,
        exhausted retries, and browser cleanup on failure.
All tests use mock Playwright objects — no real browser is launched.
"""

import pytest
from unittest.mock import patch, MagicMock

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_mocks(goto_effects: list):
    """Return a layered Playwright mock stack and the inner page mock."""
    mock_page = MagicMock()
    mock_page.goto.side_effect = goto_effects
    mock_page.url = "https://example.com/"

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw, mock_page


# ---------------------------------------------------------------------------
# crawl_page
# ---------------------------------------------------------------------------

class TestCrawlPage:
    def test_successful_crawl_returns_expected_keys(self):
        mock_response = MagicMock(status=200, headers={"content-type": "text/html"})
        mock_pw, _ = _build_mocks([mock_response])

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            result = crawl_page("https://example.com")

        for key in ("page", "browser", "playwright_obj", "status_code",
                    "response_headers", "final_url", "crawl_time"):
            assert key in result

    def test_response_headers_captured(self):
        mock_response = MagicMock(
            status=200,
            headers={"x-frame-options": "SAMEORIGIN", "content-type": "text/html"},
        )
        mock_pw, _ = _build_mocks([mock_response])

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            result = crawl_page("https://example.com")

        assert result["response_headers"]["x-frame-options"] == "SAMEORIGIN"

    def test_none_response_yields_empty_headers(self):
        """page.goto() can return None (e.g. navigation to about:blank)."""
        mock_pw, mock_page = _build_mocks([None])
        mock_page.url = "https://example.com/"

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            result = crawl_page("https://example.com")

        assert result["status_code"] is None
        assert result["response_headers"] == {}

    def test_retry_on_timeout_and_succeed(self):
        """crawl_page retries once after PlaywrightTimeoutError and succeeds."""
        mock_response = MagicMock(status=200, headers={})
        mock_pw, mock_page = _build_mocks([
            PlaywrightTimeoutError("Timeout 30000ms exceeded."),
            mock_response,
        ])

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            result = crawl_page("https://example.com")

        assert result["status_code"] == 200
        assert mock_page.goto.call_count == 2

    def test_raises_after_all_attempts_exhausted(self):
        """PlaywrightTimeoutError propagates once all attempts are used up."""
        from app.config import settings

        mock_pw, mock_page = _build_mocks(
            [PlaywrightTimeoutError("timeout")] * settings.CRAWLER_MAX_ATTEMPTS
        )

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            with pytest.raises(PlaywrightTimeoutError):
                crawl_page("https://example.com")

        assert mock_page.goto.call_count == settings.CRAWLER_MAX_ATTEMPTS

    def test_non_timeout_error_not_retried(self):
        """Errors that are not PlaywrightTimeoutError propagate on first attempt."""
        mock_pw, mock_page = _build_mocks([Exception("DNS resolution failed")])

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            with pytest.raises(Exception, match="DNS resolution failed"):
                crawl_page("https://example.com")

        # Only one goto attempt — no retry for non-timeout errors
        assert mock_page.goto.call_count == 1

    def test_browser_cleaned_up_on_failure(self):
        """Browser and Playwright instance are always released on any failure."""
        mock_pw, _ = _build_mocks([Exception("network error")])

        with patch("app.services.crawler.sync_playwright") as spi, \
             patch("app.services.crawler.time") as t:
            t.time.return_value = 0.0
            spi.return_value.start.return_value = mock_pw
            from app.services.crawler import crawl_page
            with pytest.raises(Exception):
                crawl_page("https://example.com")

        mock_pw.chromium.launch.return_value.close.assert_called()
        mock_pw.stop.assert_called()
