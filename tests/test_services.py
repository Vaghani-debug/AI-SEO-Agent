"""
Tests for all five extraction services:
  metadata, headings, images, links, technical.

All tests use mock Playwright page objects — no real browser launched.
"""

import pytest
from tests.conftest import _make_page

from app.services.metadata import extract_metadata
from app.services.headings import extract_headings
from app.services.images import extract_images
from app.services.links import extract_links
from app.services.technical import extract_technical


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

class TestExtractMetadata:
    def test_full_metadata(self, good_page):
        result = extract_metadata(good_page)
        assert result["title"] == "Test Page Title That Is Long Enough"
        assert "meta" in result["meta_description"].lower()
        assert result["canonical"] == "https://example.com/"
        assert result["robots"] is None  # good_page has robots=None

    def test_missing_all_metadata(self, bare_page):
        result = extract_metadata(bare_page)
        assert result["title"] == ""
        assert result["meta_description"] is None
        assert result["canonical"] is None
        assert result["robots"] is None

    def test_returns_dict_with_expected_keys(self, good_page):
        result = extract_metadata(good_page)
        assert set(result.keys()) == {"title", "meta_description", "canonical", "robots"}


# ---------------------------------------------------------------------------
# headings
# ---------------------------------------------------------------------------

class TestExtractHeadings:
    def test_single_valid_h1(self, good_page):
        result = extract_headings(good_page)
        assert result["h1_count"] == 1
        assert result["h1_status"] == "Valid"
        assert result["h1"] == "Main Heading"

    def test_missing_h1(self):
        page = _make_page(h1_count=0)
        result = extract_headings(page)
        assert result["h1_count"] == 0
        assert result["h1_status"] == "Missing H1"
        assert result["h1"] is None

    def test_multiple_h1(self):
        page = _make_page(h1_count=3)
        result = extract_headings(page)
        assert result["h1_count"] == 3
        assert result["h1_status"] == "Multiple H1"

    def test_h2_count(self):
        page = _make_page(h2_count=5)
        result = extract_headings(page)
        assert result["h2_count"] == 5

    def test_returns_all_heading_levels(self, good_page):
        result = extract_headings(good_page)
        for key in ("h1", "h1_status", "h1_count", "h2_count", "h3_count", "h4_count", "h5_count", "h6_count"):
            assert key in result


# ---------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------

class TestExtractImages:
    def test_all_images_have_alt(self):
        page = _make_page(image_count=4, images_missing_alt=0)
        result = extract_images(page)
        assert result["image_count"] == 4
        assert result["images_missing_alt"] == 0

    def test_some_images_missing_alt(self):
        page = _make_page(image_count=5, images_missing_alt=3)
        result = extract_images(page)
        assert result["images_missing_alt"] == 3

    def test_no_images(self):
        page = _make_page(image_count=0, images_missing_alt=0)
        result = extract_images(page)
        assert result["image_count"] == 0
        assert result["images_missing_alt"] == 0


# ---------------------------------------------------------------------------
# links
# ---------------------------------------------------------------------------

class TestExtractLinks:
    def test_internal_and_external_classification(self):
        page = _make_page(
            url="https://example.com/",
            links=[
                "https://example.com/about",   # internal absolute
                "/contact",                     # internal relative
                "https://other.com/",           # external
            ],
        )
        result = extract_links(page)
        assert result["internal_links"] == 2
        assert result["external_links"] == 1
        assert result["total_links"] == 3

    def test_fragment_anchors_ignored(self):
        page = _make_page(
            url="https://example.com/",
            links=["#top", "#footer", "https://example.com/page"],
        )
        result = extract_links(page)
        # fragments skipped; only the absolute internal link counts
        assert result["internal_links"] == 1
        assert result["external_links"] == 0

    def test_javascript_links_ignored(self):
        page = _make_page(
            url="https://example.com/",
            links=["javascript:void(0)", "https://example.com/real"],
        )
        result = extract_links(page)
        assert result["internal_links"] == 1

    def test_no_links(self):
        page = _make_page(links=[])
        result = extract_links(page)
        assert result["total_links"] == 0
        assert result["internal_links"] == 0
        assert result["external_links"] == 0


# ---------------------------------------------------------------------------
# technical
# ---------------------------------------------------------------------------

class TestExtractTechnical:
    def test_full_technical_data(self, good_page):
        result = extract_technical(good_page)
        assert result["language"] == "en"
        assert result["charset"] == "UTF-8"
        assert result["viewport"] == "width=device-width, initial-scale=1"
        assert result["og_title"] == "OG Title"
        assert result["og_description"] == "OG Description"
        assert result["og_image"] == "https://example.com/og.png"
        assert result["twitter_card"] == "summary_large_image"

    def test_missing_technical_data(self, bare_page):
        result = extract_technical(bare_page)
        assert result["language"] is None
        assert result["charset"] is None
        assert result["viewport"] is None
        assert result["og_title"] is None
        assert result["og_description"] is None
        assert result["og_image"] is None
        assert result["twitter_card"] is None

    def test_returns_expected_keys(self, good_page):
        result = extract_technical(good_page)
        for key in ("language", "charset", "viewport", "favicon", "og_title",
                    "og_description", "og_image", "twitter_card"):
            assert key in result


# ---------------------------------------------------------------------------
# structured_data
# ---------------------------------------------------------------------------

from app.services.structured_data import extract_structured_data
from tests.conftest import _make_page as make_page


class TestExtractStructuredData:
    def test_valid_jsonld_detected(self):
        page = make_page(jsonld_count=1,
                         jsonld_scripts=['{"@type":"Organization","@context":"https://schema.org"}'])
        result = extract_structured_data(page)
        assert result["has_structured_data"] is True
        assert result["valid_blocks"] == 1
        assert result["invalid_blocks"] == 0
        assert "Organization" in result["schema_types"]

    def test_no_jsonld_scripts(self):
        page = make_page(jsonld_count=0, jsonld_scripts=[])
        result = extract_structured_data(page)
        assert result["has_structured_data"] is False
        assert result["valid_blocks"] == 0
        assert result["schema_types"] == []

    def test_invalid_json_counted(self):
        page = make_page(jsonld_count=1, jsonld_scripts=["not json {{"])
        result = extract_structured_data(page)
        assert result["has_structured_data"] is False
        assert result["invalid_blocks"] == 1

    def test_array_schema_type(self):
        page = make_page(
            jsonld_count=1,
            jsonld_scripts=['[{"@type":"Article"},{"@type":"BreadcrumbList"}]'],
        )
        result = extract_structured_data(page)
        assert "Article" in result["schema_types"]
        assert "BreadcrumbList" in result["schema_types"]

    def test_multiple_valid_blocks(self):
        scripts = [
            '{"@type":"Organization"}',
            '{"@type":"WebPage"}',
        ]
        page = make_page(jsonld_count=2, jsonld_scripts=scripts)
        result = extract_structured_data(page)
        assert result["valid_blocks"] == 2
        assert result["total_blocks"] == 2


# ---------------------------------------------------------------------------
# robots_sitemap
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
from app.services.robots_sitemap import fetch_robots_data


class TestFetchRobotsData:
    def _mock_response(self, status: int, text: str = ""):
        m = MagicMock()
        m.status_code = status
        m.text = text
        return m

    def _mock_head(self, status: int):
        m = MagicMock()
        m.status_code = status
        return m

    def test_accessible_with_sitemap_in_robots(self):
        robots_body = (
            "User-agent: *\nAllow: /\n"
            "Sitemap: https://example.com/sitemap.xml\n"
        )
        with patch("app.services.robots_sitemap.httpx.get",
                   return_value=self._mock_response(200, robots_body)), \
             patch("app.services.robots_sitemap.httpx.head",
                   return_value=self._mock_head(200)):
            result = fetch_robots_data("https://example.com/page")

        assert result["robots_accessible"] is True
        assert result["sitemap_url"] == "https://example.com/sitemap.xml"
        assert result["sitemap_accessible"] is True
        assert result["disallow_all"] is False

    def test_disallow_all_detected(self):
        robots_body = "User-agent: *\nDisallow: /\n"
        with patch("app.services.robots_sitemap.httpx.get",
                   return_value=self._mock_response(200, robots_body)), \
             patch("app.services.robots_sitemap.httpx.head",
                   return_value=self._mock_head(404)):
            result = fetch_robots_data("https://example.com/")

        assert result["disallow_all"] is True

    def test_robots_not_found(self):
        with patch("app.services.robots_sitemap.httpx.get",
                   return_value=self._mock_response(404)), \
             patch("app.services.robots_sitemap.httpx.head",
                   return_value=self._mock_head(404)):
            result = fetch_robots_data("https://example.com/")

        assert result["robots_accessible"] is False

    def test_network_error_handled_gracefully(self):
        with patch("app.services.robots_sitemap.httpx.get",
                   side_effect=Exception("connection refused")), \
             patch("app.services.robots_sitemap.httpx.head",
                   side_effect=Exception("connection refused")):
            result = fetch_robots_data("https://unreachable.example/")

        assert result["robots_accessible"] is False
        assert result["sitemap_accessible"] is False

    def test_sitemap_fallback_when_not_in_robots(self):
        """When robots.txt has no Sitemap directive, /sitemap.xml is used."""
        with patch("app.services.robots_sitemap.httpx.get",
                   return_value=self._mock_response(200, "User-agent: *\nAllow: /\n")), \
             patch("app.services.robots_sitemap.httpx.head",
                   return_value=self._mock_head(200)):
            result = fetch_robots_data("https://example.com/")

        assert result["sitemap_url"] == "https://example.com/sitemap.xml"
        assert result["sitemap_accessible"] is True


# ---------------------------------------------------------------------------
# security
# ---------------------------------------------------------------------------

from app.services.security import extract_security_data


class TestExtractSecurityData:
    def _full_headers(self):
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "default-src 'self'",
            "X-Content-Type-Options": "nosniff",
        }

    def test_all_headers_present_https(self):
        result = extract_security_data(self._full_headers(), "https://example.com/")
        assert result["is_https"] is True
        assert result["has_hsts"] is True
        assert result["has_x_frame_options"] is True
        assert result["has_csp"] is True
        assert result["has_x_content_type_options"] is True

    def test_http_url_is_not_https(self):
        result = extract_security_data(self._full_headers(), "http://example.com/")
        assert result["is_https"] is False

    def test_missing_all_security_headers(self):
        result = extract_security_data({}, "https://example.com/")
        assert result["has_hsts"] is False
        assert result["has_x_frame_options"] is False
        assert result["has_csp"] is False
        assert result["has_x_content_type_options"] is False

    def test_header_names_case_insensitive(self):
        headers = {
            "strict-transport-security": "max-age=3600",
            "x-frame-options": "DENY",
        }
        result = extract_security_data(headers, "https://example.com/")
        assert result["has_hsts"] is True
        assert result["has_x_frame_options"] is True

    def test_raw_values_returned(self):
        result = extract_security_data(self._full_headers(), "https://example.com/")
        assert result["hsts_value"] == "max-age=31536000; includeSubDomains"
        assert result["x_frame_options_value"] == "SAMEORIGIN"
        assert result["csp_value"] == "default-src 'self'"

    def test_none_headers_handled_gracefully(self):
        result = extract_security_data(None, "https://example.com/")
        assert result["is_https"] is True
        assert result["has_hsts"] is False
