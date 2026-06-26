"""
Link Extraction Service.

Classifies all hyperlinks on the page as internal (same domain)
or external (different domain). Internal link density supports
site architecture and crawlability; external links signal authority.
"""

from urllib.parse import urlparse


def extract_links(page) -> dict:
    """
    Classify all <a href> links as internal or external.

    Parameters:
        page: Playwright page object (must already be navigated).

    Returns:
        dict with keys: total_links, internal_links, external_links.
    """
    links = page.locator("a")
    total_links = links.count()
    internal_links = 0
    external_links = 0

    # Extract the domain of the current page for comparison
    current_domain = urlparse(page.url).netloc

    for i in range(total_links):
        href = links.nth(i).get_attribute("href")

        if not href:
            continue  # skip anchors with no href attribute
        if href.startswith("#"):
            continue  # skip same-page fragment anchors
        if href.startswith("javascript:"):
            continue  # skip non-navigational pseudo-links

        # Relative paths (e.g. /about) always belong to the current domain
        if href.startswith("/"):
            internal_links += 1
            continue

        # For absolute URLs, compare netloc to determine internal vs external
        parsed = urlparse(href)
        if parsed.netloc == "" or parsed.netloc == current_domain:
            internal_links += 1
        else:
            external_links += 1

    return {
        "total_links": total_links,
        "internal_links": internal_links,
        "external_links": external_links,
    }
