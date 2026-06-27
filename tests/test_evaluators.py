"""
Tests for app/evaluators/seo_evaluator.py and app/evaluators/score_calculator.py

Covers: every issue rule, edge cases, score deductions, and grade boundaries.
"""

import pytest

from app.evaluators.seo_evaluator import evaluate_seo
from app.evaluators.score_calculator import calculate_seo_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_types(issues):
    return [i["issue"] for i in issues]


def _severities(issues):
    return [i["severity"] for i in issues]


def _base_data(**overrides) -> dict:
    """
    Build a minimal seo_data dict that passes all rules by default.
    Individual keys can be overridden to trigger specific issues.
    """
    data = {
        "request": {"http_status": 200},
        "technical": {
            "language": "en",
            "viewport": "width=device-width, initial-scale=1",
            "charset": "UTF-8",
            "og_title": "OG Title",
            "og_description": "OG Description",
            "og_image": "https://example.com/og.png",
            "twitter_card": "summary_large_image",
        },
        "metadata": {
            "title": "A well-optimized page title exactly right",
            "meta_description": (
                "A well-crafted meta description that sits comfortably between "
                "120 and 160 characters to pass the length validation rule cleanly."
            ),
            "canonical": "https://example.com/",
        },
        "heading_data": {"h1_count": 1},
        "image_data": {"images_missing_alt": 0},
        "link_data": {"internal_links": 5},
        "structured_data": {
            "has_structured_data": True,
            "invalid_blocks": 0,
            "valid_blocks": 1,
            "total_blocks": 1,
            "schema_types": ["Organization"],
        },
        "robots_data": {
            "robots_accessible": True,
            "disallow_all": False,
            "sitemap_accessible": True,
            "robots_url": "https://example.com/robots.txt",
            "sitemap_url": "https://example.com/sitemap.xml",
        },
        "security": {
            "is_https": True,
            "has_hsts": True,
            "has_x_frame_options": True,
            "has_csp": True,
            "has_x_content_type_options": True,
            "hsts_value": "max-age=31536000; includeSubDomains",
            "x_frame_options_value": "SAMEORIGIN",
            "csp_value": "default-src 'self'",
        },
    }
    # Apply flat overrides to any nested dict key
    for path, value in overrides.items():
        section, key = path.split(".", 1)
        data[section][key] = value
    return data


# ---------------------------------------------------------------------------
# HTTP status
# ---------------------------------------------------------------------------

class TestHttpStatus:
    def test_200_no_issue(self):
        issues = evaluate_seo(_base_data())
        assert not any("HTTP Status" in i["issue"] for i in issues)

    def test_404_raises_high_issue(self):
        issues = evaluate_seo(_base_data(**{"request.http_status": 404}))
        assert any("HTTP Status" in i["issue"] for i in issues)
        http_issues = [i for i in issues if "HTTP Status" in i["issue"]]
        assert http_issues[0]["severity"] == "High"

    def test_500_raises_high_issue(self):
        issues = evaluate_seo(_base_data(**{"request.http_status": 500}))
        assert any("HTTP Status" in i["issue"] for i in issues)


# ---------------------------------------------------------------------------
# Technical SEO rules
# ---------------------------------------------------------------------------

class TestTechnicalRules:
    def test_missing_language_low_severity(self):
        issues = evaluate_seo(_base_data(**{"technical.language": None}))
        lang_issues = [i for i in issues if "language" in i["issue"].lower()]
        assert lang_issues, "Expected a language issue"
        assert lang_issues[0]["severity"] == "Low"

    def test_missing_viewport_high_severity(self):
        issues = evaluate_seo(_base_data(**{"technical.viewport": None}))
        vp_issues = [i for i in issues if "viewport" in i["issue"].lower()]
        assert vp_issues, "Expected a viewport issue"
        assert vp_issues[0]["severity"] == "High"

    def test_missing_charset_medium_severity(self):
        issues = evaluate_seo(_base_data(**{"technical.charset": None}))
        cs_issues = [i for i in issues if "charset" in i["issue"].lower()]
        assert cs_issues, "Expected a charset issue"
        assert cs_issues[0]["severity"] == "Medium"


# ---------------------------------------------------------------------------
# Open Graph and Twitter Card
# ---------------------------------------------------------------------------

class TestSocialTags:
    def test_missing_og_title_medium(self):
        issues = evaluate_seo(_base_data(**{"technical.og_title": None}))
        og = [i for i in issues if "og:title" in i["issue"]]
        assert og and og[0]["severity"] == "Medium"

    def test_missing_og_description_medium(self):
        issues = evaluate_seo(_base_data(**{"technical.og_description": None}))
        og = [i for i in issues if "og:description" in i["issue"]]
        assert og and og[0]["severity"] == "Medium"

    def test_missing_og_image_medium(self):
        issues = evaluate_seo(_base_data(**{"technical.og_image": None}))
        og = [i for i in issues if "og:image" in i["issue"]]
        assert og and og[0]["severity"] == "Medium"

    def test_missing_twitter_card_low(self):
        issues = evaluate_seo(_base_data(**{"technical.twitter_card": None}))
        tc = [i for i in issues if "Twitter" in i["issue"]]
        assert tc and tc[0]["severity"] == "Low"

    def test_all_social_tags_present_no_issue(self):
        issues = evaluate_seo(_base_data())
        social = [i for i in issues if i["category"] == "Social SEO"]
        assert not social


# ---------------------------------------------------------------------------
# Metadata rules
# ---------------------------------------------------------------------------

class TestMetadataRules:
    def test_missing_title_high(self):
        issues = evaluate_seo(_base_data(**{"metadata.title": None}))
        title_issues = [i for i in issues if "title" in i["issue"].lower() and "Missing" in i["issue"]]
        assert title_issues and title_issues[0]["severity"] == "High"

    def test_short_title_low(self):
        issues = evaluate_seo(_base_data(**{"metadata.title": "Hi"}))
        short = [i for i in issues if "Title too short" in i["issue"]]
        assert short and short[0]["severity"] == "Low"

    def test_long_title_medium(self):
        issues = evaluate_seo(_base_data(**{"metadata.title": "X" * 61}))
        long = [i for i in issues if "Title too long" in i["issue"]]
        assert long and long[0]["severity"] == "Medium"

    def test_title_exactly_60_chars_no_issue(self):
        issues = evaluate_seo(_base_data(**{"metadata.title": "X" * 60}))
        assert not any("Title too long" in i["issue"] for i in issues)

    def test_title_exactly_30_chars_no_issue(self):
        issues = evaluate_seo(_base_data(**{"metadata.title": "X" * 30}))
        assert not any("Title too short" in i["issue"] for i in issues)

    def test_missing_description_high(self):
        issues = evaluate_seo(_base_data(**{"metadata.meta_description": None}))
        desc = [i for i in issues if "meta description" in i["issue"].lower() and "Missing" in i["issue"]]
        assert desc and desc[0]["severity"] == "High"

    def test_short_description_low(self):
        issues = evaluate_seo(_base_data(**{"metadata.meta_description": "Short."}))
        short = [i for i in issues if "description too short" in i["issue"].lower()]
        assert short and short[0]["severity"] == "Low"

    def test_long_description_medium(self):
        issues = evaluate_seo(_base_data(**{"metadata.meta_description": "X" * 161}))
        long = [i for i in issues if "description too long" in i["issue"].lower()]
        assert long and long[0]["severity"] == "Medium"

    def test_missing_canonical_medium(self):
        issues = evaluate_seo(_base_data(**{"metadata.canonical": None}))
        can = [i for i in issues if "canonical" in i["issue"].lower()]
        assert can and can[0]["severity"] == "Medium"


# ---------------------------------------------------------------------------
# Heading rules
# ---------------------------------------------------------------------------

class TestHeadingRules:
    def test_missing_h1_high(self):
        issues = evaluate_seo(_base_data(**{"heading_data.h1_count": 0}))
        h1 = [i for i in issues if "H1" in i["issue"] and "Missing" in i["issue"]]
        assert h1 and h1[0]["severity"] == "High"

    def test_multiple_h1_medium(self):
        issues = evaluate_seo(_base_data(**{"heading_data.h1_count": 3}))
        multi = [i for i in issues if "Multiple H1" in i["issue"]]
        assert multi and multi[0]["severity"] == "Medium"

    def test_single_h1_no_issue(self):
        issues = evaluate_seo(_base_data())
        h1_issues = [i for i in issues if "H1" in i["issue"]]
        assert not h1_issues


# ---------------------------------------------------------------------------
# Image ALT rules
# ---------------------------------------------------------------------------

class TestImageRules:
    def test_images_missing_alt_medium(self):
        issues = evaluate_seo(_base_data(**{"image_data.images_missing_alt": 4}))
        alt = [i for i in issues if "missing ALT" in i["issue"]]
        assert alt and alt[0]["severity"] == "Medium"

    def test_no_missing_alt_no_issue(self):
        issues = evaluate_seo(_base_data())
        assert not any("ALT" in i["issue"] for i in issues)


# ---------------------------------------------------------------------------
# Link rules
# ---------------------------------------------------------------------------

class TestLinkRules:
    def test_no_internal_links_high(self):
        issues = evaluate_seo(_base_data(**{"link_data.internal_links": 0}))
        links = [i for i in issues if "internal links" in i["issue"].lower()]
        assert links and links[0]["severity"] == "High"

    def test_has_internal_links_no_issue(self):
        issues = evaluate_seo(_base_data())
        assert not any("internal links" in i["issue"].lower() for i in issues)


# ---------------------------------------------------------------------------
# Score calculator
# ---------------------------------------------------------------------------

class TestScoreCalculator:
    def test_perfect_score_no_issues(self):
        result = calculate_seo_score([])
        assert result["score"] == 100
        assert result["grade"] == "A"

    def test_single_high_issue(self):
        result = calculate_seo_score([{"severity": "High"}])
        assert result["score"] == 85
        assert result["grade"] == "B"

    def test_single_medium_issue(self):
        result = calculate_seo_score([{"severity": "Medium"}])
        assert result["score"] == 93
        assert result["grade"] == "A"

    def test_single_low_issue(self):
        result = calculate_seo_score([{"severity": "Low"}])
        assert result["score"] == 97
        assert result["grade"] == "A"

    def test_score_clamped_to_zero(self):
        many_high = [{"severity": "High"}] * 20  # 20 * 15 = 300 > 100
        result = calculate_seo_score(many_high)
        assert result["score"] == 0
        assert result["grade"] == "F"

    def test_grade_boundaries(self):
        # A ≥ 90
        assert calculate_seo_score([])["grade"] == "A"
        # B 80-89
        assert calculate_seo_score([{"severity": "High"}])["grade"] == "B"
        # C 70-79: need 21-30 pts deducted from 100; 3 high = 55 (F), use mediums
        # 100 - 3*7 = 79 → C
        three_medium = [{"severity": "Medium"}] * 3
        assert calculate_seo_score(three_medium)["grade"] == "C"
        # D 60-69: 100 - 4*7 = 72 (C). 100 - 2*15 = 70 (C). 100 - 3*15 = 55 (F).
        # 100 - 5*7 = 65 → D
        five_medium = [{"severity": "Medium"}] * 5
        assert calculate_seo_score(five_medium)["grade"] == "D"
        # F < 60: 100 - 6*7 = 58
        six_medium = [{"severity": "Medium"}] * 6
        assert calculate_seo_score(six_medium)["grade"] == "F"

    def test_unknown_severity_ignored(self):
        result = calculate_seo_score([{"severity": "Unknown"}])
        assert result["score"] == 100

    def test_mixed_severities(self):
        issues = [
            {"severity": "High"},    # -15  → 85
            {"severity": "Medium"},  # -7   → 78
            {"severity": "Low"},     # -3   → 75
        ]
        result = calculate_seo_score(issues)
        assert result["score"] == 75
        assert result["grade"] == "C"


# ---------------------------------------------------------------------------
# Structured data rules
# ---------------------------------------------------------------------------

class TestStructuredDataRules:
    def test_no_structured_data_medium(self):
        issues = evaluate_seo(_base_data(**{"structured_data.has_structured_data": False}))
        sd = [i for i in issues if "structured data" in i["issue"].lower()]
        assert sd and sd[0]["severity"] == "Medium"

    def test_invalid_blocks_medium(self):
        data = _base_data()
        data["structured_data"]["invalid_blocks"] = 2
        issues = evaluate_seo(data)
        invalid = [i for i in issues if "invalid JSON-LD" in i["issue"]]
        assert invalid and invalid[0]["severity"] == "Medium"

    def test_valid_structured_data_no_issue(self):
        issues = evaluate_seo(_base_data())
        sd_issues = [i for i in issues if i["category"] == "Structured Data"]
        assert not sd_issues

    def test_missing_key_skipped_gracefully(self):
        """If structured_data key absent entirely, no crash and no SD issues."""
        data = _base_data()
        del data["structured_data"]
        issues = evaluate_seo(data)
        assert not any(i["category"] == "Structured Data" for i in issues)


# ---------------------------------------------------------------------------
# Robots / sitemap rules
# ---------------------------------------------------------------------------

class TestRobotsSitemapRules:
    def test_robots_not_accessible_medium(self):
        issues = evaluate_seo(_base_data(**{"robots_data.robots_accessible": False}))
        rb = [i for i in issues if "robots.txt" in i["issue"]]
        assert rb and rb[0]["severity"] == "Medium"

    def test_disallow_all_high(self):
        issues = evaluate_seo(_base_data(**{"robots_data.disallow_all": True}))
        block = [i for i in issues if "blocks all" in i["issue"]]
        assert block and block[0]["severity"] == "High"

    def test_sitemap_not_accessible_medium(self):
        issues = evaluate_seo(_base_data(**{"robots_data.sitemap_accessible": False}))
        sm = [i for i in issues if "sitemap" in i["issue"].lower()]
        assert sm and sm[0]["severity"] == "Medium"

    def test_healthy_robots_no_issues(self):
        issues = evaluate_seo(_base_data())
        assert not any(i["category"] == "Crawlability" for i in issues)

    def test_missing_robots_key_skipped(self):
        data = _base_data()
        del data["robots_data"]
        issues = evaluate_seo(data)
        assert not any(i["category"] == "Crawlability" for i in issues)


# ---------------------------------------------------------------------------
# Security header rules
# ---------------------------------------------------------------------------

class TestSecurityRules:
    def test_no_https_high(self):
        issues = evaluate_seo(_base_data(**{"security.is_https": False}))
        https_issues = [i for i in issues if "HTTPS" in i["issue"]]
        assert https_issues and https_issues[0]["severity"] == "High"

    def test_missing_hsts_medium(self):
        issues = evaluate_seo(_base_data(**{"security.has_hsts": False}))
        hsts = [i for i in issues if "HSTS" in i["issue"]]
        assert hsts and hsts[0]["severity"] == "Medium"

    def test_missing_x_frame_options_low(self):
        issues = evaluate_seo(_base_data(**{"security.has_x_frame_options": False}))
        xfo = [i for i in issues if "X-Frame-Options" in i["issue"]]
        assert xfo and xfo[0]["severity"] == "Low"

    def test_missing_csp_medium(self):
        issues = evaluate_seo(_base_data(**{"security.has_csp": False}))
        csp = [i for i in issues if "Content-Security-Policy" in i["issue"]]
        assert csp and csp[0]["severity"] == "Medium"

    def test_missing_xcto_low(self):
        issues = evaluate_seo(_base_data(**{"security.has_x_content_type_options": False}))
        xcto = [i for i in issues if "X-Content-Type-Options" in i["issue"]]
        assert xcto and xcto[0]["severity"] == "Low"

    def test_all_security_headers_present_no_issues(self):
        issues = evaluate_seo(_base_data())
        assert not any(i["category"] == "Security" for i in issues)

    def test_missing_security_key_skipped(self):
        data = _base_data()
        del data["security"]
        issues = evaluate_seo(data)
        assert not any(i["category"] == "Security" for i in issues)
