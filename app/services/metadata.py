"""
Metadata extraction service.

This module is responsible for extracting basic SEO metadata
from an already opened Playwright page.
"""

# Import helper functions
from app.utils.helpers import safe_attribute


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