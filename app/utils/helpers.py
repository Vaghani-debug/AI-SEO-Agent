"""
Shared Utility Helpers.

Provides safe DOM access wrappers for Playwright locators and
URL normalisation used across all extraction services.
"""

from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """
    Ensure the URL has an explicit scheme.

    Adds https:// when the user omits the scheme so that
    Playwright can navigate and urllib can parse the domain.

    Parameters:
        url: Raw URL string from the API request.

    Returns:
        str: URL guaranteed to start with http:// or https://.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def safe_text(locator) -> str | None:
    """
    Safely return the text content of the first matching element.

    Returns None instead of raising if the element does not exist
    or if Playwright raises an unexpected error.

    Parameters:
        locator: Playwright Locator object.

    Returns:
        str: Stripped text content, or None if unavailable.
    """
    try:
        if locator.count() == 0:
            return None
        text = locator.first.text_content()
        return text.strip() if text else None
    except Exception:
        return None


def safe_attribute(locator, attribute: str) -> str | None:
    """
    Safely return an HTML attribute value from the first matching element.

    Returns None instead of raising if the element does not exist
    or if the attribute is not present.

    Parameters:
        locator:   Playwright Locator object.
        attribute: Name of the HTML attribute to read.

    Returns:
        str: Attribute value, or None if the element or attribute is absent.
    """
    try:
        if locator.count() == 0:
            return None
        return locator.first.get_attribute(attribute)
    except Exception:
        return None
