"""
Heading extraction service.

This module extracts heading information (H1-H6)
from a webpage for SEO analysis.
"""


def extract_headings(page):
    """
    Extract heading structure from a webpage.

    Parameters:
        page: Playwright page object

    Returns:
        dict: Heading SEO information.
    """

    # Count all heading levels
    h1_count = page.locator("h1").count()
    h2_count = page.locator("h2").count()
    h3_count = page.locator("h3").count()
    h4_count = page.locator("h4").count()
    h5_count = page.locator("h5").count()
    h6_count = page.locator("h6").count()

    # Get the first H1 text (if available)
    first_h1 = None
    if h1_count > 0:
        first_h1 = " ".join(page.locator("h1").first.text_content().split())

    # Determine heading status
    if h1_count == 0:
        h1_status = "Missing H1"

    elif h1_count == 1:
        h1_status = "Valid"

    else:
        h1_status = "Multiple H1"

    return {

        # First H1 text
        "h1": first_h1,

        # H1 status
        "h1_status": h1_status,

        # Heading counts
        "h1_count": h1_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "h4_count": h4_count,
        "h5_count": h5_count,
        "h6_count": h6_count

    }