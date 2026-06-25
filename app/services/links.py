"""
Link extraction service.

This module extracts basic link information
from a webpage.
"""


from urllib.parse import urlparse


def extract_links(page):
    """
    Extract basic link information.

    Parameters:
        page: Playwright page object

    Returns:
        dict
    """

    # Find every hyperlink
    links = page.locator("a")

    # Count total links
    total_links = links.count()

    # Counters
    internal_links = 0
    external_links = 0

    # Current website domain
    current_domain = urlparse(page.url).netloc

    # Loop through every link
    for i in range(total_links):

        href = links.nth(i).get_attribute("href")

        if not href:
            continue

        # Ignore anchors
        if href.startswith("#"):
            continue

        # Ignore JavaScript links
        if href.startswith("javascript:"):
            continue

        # Relative URL = internal
        if href.startswith("/"):
            internal_links += 1
            continue

        # Absolute URL
        parsed = urlparse(href)

        if parsed.netloc == "" or parsed.netloc == current_domain:
            internal_links += 1
        else:
            external_links += 1

    return {

        "total_links": total_links,

        "internal_links": internal_links,

        "external_links": external_links

    }