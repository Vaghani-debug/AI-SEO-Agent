"""
Tests for app/utils/helpers.py

Covers: normalize_url, safe_text, safe_attribute.
"""

import pytest
from unittest.mock import MagicMock

from app.utils.helpers import normalize_url, safe_text, safe_attribute


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------

class TestNormalizeUrl:
    def test_bare_domain_gets_https(self):
        assert normalize_url("example.com") == "https://example.com"

    def test_https_unchanged(self):
        assert normalize_url("https://example.com/path") == "https://example.com/path"

    def test_http_unchanged(self):
        assert normalize_url("http://example.com") == "http://example.com"

    def test_leading_whitespace_stripped(self):
        assert normalize_url("  example.com  ") == "https://example.com"

    def test_path_preserved(self):
        result = normalize_url("example.com/some/path?q=1")
        assert result == "https://example.com/some/path?q=1"


# ---------------------------------------------------------------------------
# safe_text
# ---------------------------------------------------------------------------

class TestSafeText:
    def _locator(self, count, text):
        loc = MagicMock()
        loc.count.return_value = count
        loc.first.text_content.return_value = text
        return loc

    def test_returns_text_when_element_exists(self):
        assert safe_text(self._locator(1, "  Hello  ")) == "Hello"

    def test_returns_none_when_no_element(self):
        assert safe_text(self._locator(0, "Hello")) is None

    def test_returns_none_on_empty_string(self):
        assert safe_text(self._locator(1, "")) is None

    def test_returns_none_on_playwright_exception(self):
        loc = MagicMock()
        loc.count.side_effect = Exception("playwright error")
        assert safe_text(loc) is None


# ---------------------------------------------------------------------------
# safe_attribute
# ---------------------------------------------------------------------------

class TestSafeAttribute:
    def _locator(self, count, attr_value):
        loc = MagicMock()
        loc.count.return_value = count
        loc.first.get_attribute.return_value = attr_value
        return loc

    def test_returns_attribute_when_element_exists(self):
        assert safe_attribute(self._locator(1, "en"), "lang") == "en"

    def test_returns_none_when_no_element(self):
        assert safe_attribute(self._locator(0, "en"), "lang") is None

    def test_returns_none_when_attribute_absent(self):
        assert safe_attribute(self._locator(1, None), "lang") is None

    def test_returns_none_on_playwright_exception(self):
        loc = MagicMock()
        loc.count.side_effect = Exception("playwright error")
        assert safe_attribute(loc, "lang") is None
