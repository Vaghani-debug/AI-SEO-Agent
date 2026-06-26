"""
Metadata Extraction Service.

Extracts core on-page SEO metadata from a Playwright page:
title, meta description, canonical URL, and robots directive.
"""

from app.utils.helpers import safe_attribute


def extract_metadata(page) -> dict:
    """
    Extract SEO metadata from the loaded page.

    Parameters:
        page: Playwright page object (must already be navigated).

    Returns:
        dict with keys: title, meta_description, canonical, robots.
    """
    return {
        # <title> tag text content
        "title": page.title(),
        # <meta name="description" content="..."> value
        "meta_description": safe_attribute(page.locator("meta[name='description']"), "content"),
        # <link rel="canonical" href="..."> -- prevents duplicate content penalties
        "canonical": safe_attribute(page.locator("link[rel='canonical']"), "href"),
        # <meta name="robots" content="..."> -- controls search engine crawl behaviour
        "robots": safe_attribute(page.locator("meta[name='robots']"), "content"),
    }
