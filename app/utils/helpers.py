from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """Ensure the URL includes http:// or https://."""
    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def safe_text(locator):
    """Safely return text from a Playwright locator."""
    try:
        if locator.count() == 0:
            return None

        text = locator.first.text_content()
        return text.strip() if text else None


    except Exception:
        return None


def safe_attribute(locator, attribute):
    """Safely return an attribute from a Playwright locator."""
    try:
        if locator.count() == 0:
            return None

        return locator.first.get_attribute(attribute)

    except Exception:
        return None