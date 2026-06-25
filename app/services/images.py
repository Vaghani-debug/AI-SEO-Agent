"""
Image SEO extraction service.

This module analyzes images on a webpage.
"""


def extract_images(page):
    """
    Extract image-related SEO information.

    Parameters:
        page: Playwright page object

    Returns:
        dict: Image SEO information.
    """

    # Find all images
    images = page.locator("img")

    # Count total images
    image_count = images.count()

    # Counter for images missing ALT text
    images_missing_alt = 0

    # Loop through every image
    for i in range(image_count):

        alt = images.nth(i).get_attribute("alt")

        if not alt or alt.strip() == "":
            images_missing_alt += 1

    return {

        "image_count": image_count,

        "images_missing_alt": images_missing_alt

    }