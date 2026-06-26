"""
Technical SEO extraction service.

Extracts basic technical SEO information.
"""

# Import helper function
from app.utils.helpers import safe_attribute


def extract_technical(page):
    """
    Extract technical SEO information.

    Parameters:
        page: Playwright page object

    Returns:
        dict
    """

    return {

        # HTML language
        "language": safe_attribute(
            page.locator("html"),
            "lang"
        ),

        # Character encoding
        "charset": safe_attribute(
            page.locator("meta[charset]"),
            "charset"
        ),

        # Mobile viewport
        "viewport": safe_attribute(
            page.locator("meta[name='viewport']"),
            "content"
        ),

        # Favicon
        "favicon": safe_attribute(
            page.locator("link[rel='icon']"),
            "href"
        ),

        # Open Graph title
        "og_title": safe_attribute(
            page.locator("meta[property='og:title']"),
            "content"
        ),

        # Open Graph description
        "og_description": safe_attribute(
            page.locator("meta[property='og:description']"),
            "content"
        ),

        # Open Graph image
        "og_image": safe_attribute(
            page.locator("meta[property='og:image']"),
            "content"
        ),

        # Twitter Card
        "twitter_card": safe_attribute(
            page.locator("meta[name='twitter:card']"),
            "content"
        )

    }