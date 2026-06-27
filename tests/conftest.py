"""
Shared pytest fixtures for the AI SEO Agent test suite.

Provides lightweight mock Playwright page objects so that every
extractor and evaluator can be unit-tested without launching a
real browser.
"""

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Playwright page mock helpers
# ---------------------------------------------------------------------------

def _make_locator(count: int = 0, text: str = "", attribute_map: dict | None = None):
    """Return a MagicMock that mimics a Playwright Locator."""
    locator = MagicMock()
    locator.count.return_value = count
    locator.first.text_content.return_value = text
    locator.first.get_attribute.side_effect = lambda attr: (attribute_map or {}).get(attr)
    # Support .nth(i) chaining used by images and links extractors
    locator.nth.return_value = locator.first
    return locator


def _make_page(
    title: str = "Test Page Title That Is Long Enough",
    meta_description: str = "A meta description that meets the minimum length requirement for SEO purposes.",
    canonical: str = "https://example.com/",
    robots: str = None,
    lang: str = "en",
    charset: str = "UTF-8",
    viewport: str = "width=device-width, initial-scale=1",
    favicon: str = "/favicon.ico",
    og_title: str = "OG Title",
    og_description: str = "OG Description",
    og_image: str = "https://example.com/og.png",
    twitter_card: str = "summary_large_image",
    h1_count: int = 1,
    h1_text: str = "Main Heading",
    h2_count: int = 2,
    image_count: int = 3,
    images_missing_alt: int = 0,
    url: str = "https://example.com/",
    links: list | None = None,
    jsonld_count: int = 1,
    jsonld_scripts: list | None = None,
):
    """
    Build a mock Playwright page with fully configurable SEO properties.

    Keyword args mirror the SEO signals used across all extraction services.
    """
    page = MagicMock()
    page.url = url
    page.title.return_value = title

    # --- locator factory -------------------------------------------------
    def locator(selector):  # noqa: WPS430
        """Return a tailored mock locator based on the CSS selector."""

        if selector == "meta[name='description']":
            return _make_locator(1 if meta_description else 0, attribute_map={"content": meta_description})
        if selector == "link[rel='canonical']":
            return _make_locator(1 if canonical else 0, attribute_map={"href": canonical})
        if selector == "meta[name='robots']":
            return _make_locator(1 if robots else 0, attribute_map={"content": robots})
        if selector == "html":
            return _make_locator(1, attribute_map={"lang": lang})
        if selector == "meta[charset]":
            return _make_locator(1 if charset else 0, attribute_map={"charset": charset})
        if selector == "meta[name='viewport']":
            return _make_locator(1 if viewport else 0, attribute_map={"content": viewport})
        if selector == "link[rel='icon']":
            return _make_locator(1 if favicon else 0, attribute_map={"href": favicon})
        if selector == "meta[property='og:title']":
            return _make_locator(1 if og_title else 0, attribute_map={"content": og_title})
        if selector == "meta[property='og:description']":
            return _make_locator(1 if og_description else 0, attribute_map={"content": og_description})
        if selector == "meta[property='og:image']":
            return _make_locator(1 if og_image else 0, attribute_map={"content": og_image})
        if selector == "meta[name='twitter:card']":
            return _make_locator(1 if twitter_card else 0, attribute_map={"content": twitter_card})

        # heading selectors
        for tag, count in [
            ("h1", h1_count), ("h2", h2_count), ("h3", 0),
            ("h4", 0), ("h5", 0), ("h6", 0),
        ]:
            if selector == tag:
                loc = _make_locator(count, text=h1_text if tag == "h1" else "")
                loc.first.text_content.return_value = h1_text if (tag == "h1" and count > 0) else ""
                return loc

        # images
        if selector == "img":
            img_loc = MagicMock()
            img_loc.count.return_value = image_count
            def _nth_img(i):
                m = MagicMock()
                # first `images_missing_alt` images have no alt
                m.get_attribute.return_value = None if i < images_missing_alt else "alt text"
                return m
            img_loc.nth.side_effect = _nth_img
            return img_loc

        # links
        if selector == "a":
            resolved_links = links if links is not None else [
                "https://example.com/page1",
                "https://example.com/page2",
                "https://other.com/",
            ]
            link_loc = MagicMock()
            link_loc.count.return_value = len(resolved_links)
            def _nth_link(i):
                m = MagicMock()
                m.get_attribute.return_value = resolved_links[i]
                return m
            link_loc.nth.side_effect = _nth_link
            return link_loc

        # JSON-LD structured data scripts
        if selector == "script[type='application/ld+json']":
            default_scripts = ['{"@type": "Organization", "@context": "https://schema.org"}']
            resolved_scripts = jsonld_scripts if jsonld_scripts is not None else default_scripts
            actual_count = jsonld_count
            script_loc = MagicMock()
            script_loc.count.return_value = actual_count
            def _nth_script(i):
                m = MagicMock()
                m.text_content.return_value = (
                    resolved_scripts[i] if i < len(resolved_scripts) else resolved_scripts[0]
                )
                return m
            script_loc.nth.side_effect = _nth_script
            return script_loc

        return _make_locator(0)

    page.locator.side_effect = locator
    return page


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def good_page():
    """A fully SEO-healthy mock page — should produce zero issues."""
    return _make_page()


@pytest.fixture
def bare_page():
    """
    A minimal mock page missing almost every optional SEO signal.
    Used to verify that evaluator rules fire correctly.
    """
    return _make_page(
        title="",
        meta_description="",
        canonical=None,
        robots=None,
        lang=None,
        charset=None,
        viewport=None,
        favicon=None,
        og_title=None,
        og_description=None,
        og_image=None,
        twitter_card=None,
        h1_count=0,
        image_count=2,
        images_missing_alt=2,
        links=[],
    )
