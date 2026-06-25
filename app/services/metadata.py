"""
Metadata extraction service.

This module is responsible for extracting basic SEO metadata
from an already opened Playwright page.
"""

# Import helper functions
from app.utils.helpers import safe_attribute, safe_text


def extract_metadata(page):
    """
    Extract basic SEO metadata from the webpage.

    Parameters:
        page: Playwright page object

    Returns:
        dict: Dictionary containing metadata.
    """

    return {

        # Page title
        "title": page.title(),

        # Meta description
        "meta_description": safe_attribute(
            page.locator("meta[name='description']"),
            "content"
        ),

        # First H1 tag
        "h1": safe_text(
            page.locator("h1")
        ),

        # Canonical URL
        "canonical": safe_attribute(
            page.locator("link[rel='canonical']"),
            "href"
        ),

        # Robots meta tag
        "robots": safe_attribute(
            page.locator("meta[name='robots']"),
            "content"
        )
    }