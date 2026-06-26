"""
Technical SEO Extraction Service.

Extracts technical and social metadata that affects search engine
rendering, mobile usability, and social media sharing:
  - HTML language attribute
  - Character encoding (charset)
  - Mobile viewport meta tag
  - Favicon
  - Open Graph tags  (og:title, og:description, og:image)
  - Twitter Card meta tag
"""

from app.utils.helpers import safe_attribute


def extract_technical(page) -> dict:
    """
    Extract technical and social SEO metadata from the loaded page.

    Parameters:
        page: Playwright page object (must already be navigated).

    Returns:
        dict of technical signal values; None for any absent tag.
    """
    return {
        # lang attribute on <html> -- signals page language to search engines and assistive tech
        "language": safe_attribute(page.locator("html"), "lang"),
        # <meta charset="..."> -- UTF-8 is the expected standard for all modern pages
        "charset": safe_attribute(page.locator("meta[charset]"), "charset"),
        # <meta name="viewport"> -- required for mobile-friendly rendering (Core Web Vitals)
        "viewport": safe_attribute(page.locator("meta[name='viewport']"), "content"),
        # <link rel="icon"> -- favicon referenced by browsers and some search result snippets
        "favicon": safe_attribute(page.locator("link[rel='icon']"), "href"),
        # Open Graph tags -- control appearance when the page is shared on Facebook / LinkedIn
        "og_title":       safe_attribute(page.locator("meta[property='og:title']"), "content"),
        "og_description": safe_attribute(page.locator("meta[property='og:description']"), "content"),
        "og_image":       safe_attribute(page.locator("meta[property='og:image']"), "content"),
        # Twitter Card -- controls appearance when the page is shared on X / Twitter
        "twitter_card": safe_attribute(page.locator("meta[name='twitter:card']"), "content"),
    }
