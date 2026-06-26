"""
Heading Extraction Service.

Extracts the heading structure (H1-H6) from a Playwright page.
Heading hierarchy is a key on-page SEO signal: every page should
have exactly one H1 that clearly describes the page topic.
"""


def extract_headings(page) -> dict:
    """
    Count all heading levels and retrieve the first H1 text.

    Parameters:
        page: Playwright page object (must already be navigated).

    Returns:
        dict with keys: h1, h1_status, h1_count, h2_count .. h6_count.
    """
    # Count each heading level independently
    h1_count = page.locator("h1").count()
    h2_count = page.locator("h2").count()
    h3_count = page.locator("h3").count()
    h4_count = page.locator("h4").count()
    h5_count = page.locator("h5").count()
    h6_count = page.locator("h6").count()

    # Retrieve and normalise the first H1 text only when one exists.
    # str.split() + join collapses all internal whitespace and strips newlines.
    first_h1 = None
    if h1_count > 0:
        first_h1 = " ".join(page.locator("h1").first.text_content().split())

    # Determine the H1 validity status for the evaluator
    if h1_count == 0:
        h1_status = "Missing H1"
    elif h1_count == 1:
        h1_status = "Valid"
    else:
        h1_status = "Multiple H1"

    return {
        "h1": first_h1,
        "h1_status": h1_status,
        "h1_count": h1_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "h4_count": h4_count,
        "h5_count": h5_count,
        "h6_count": h6_count,
    }
