"""
Image SEO Extraction Service.

Analyses <img> elements to detect accessibility and SEO issues.
Images without ALT text are invisible to search engines and
inaccessible to users relying on screen readers.
"""


def extract_images(page) -> dict:
    """
    Count total images and images missing ALT text.

    Parameters:
        page: Playwright page object (must already be navigated).

    Returns:
        dict with keys: image_count, images_missing_alt.
    """
    images = page.locator("img")
    image_count = images.count()
    images_missing_alt = 0

    for i in range(image_count):
        alt = images.nth(i).get_attribute("alt")
        # Flag images with no alt attribute or a blank/whitespace-only value
        if not alt or alt.strip() == "":
            images_missing_alt += 1

    return {
        "image_count": image_count,
        "images_missing_alt": images_missing_alt,
    }
