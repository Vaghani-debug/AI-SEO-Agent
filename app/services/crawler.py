from playwright.sync_api import sync_playwright


def audit_page(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")

        title = page.title()

        meta_description = page.locator("meta[name='description']").get_attribute("content")

        h1 = page.locator("h1").first.text_content() if page.locator("h1").count() > 0 else None

        canonical = page.locator("link[rel='canonical']").get_attribute("href")

        robots = page.locator("meta[name='robots']").get_attribute("content")

        images = page.locator("img")

        image_count = images.count()

        images_missing_alt = 0

        for i in range(image_count):
            alt = images.nth(i).get_attribute("alt")
            if not alt:
                images_missing_alt += 1

        browser.close()

        return {
            "url": url,
            "title": title,
            "meta_description": meta_description,
            "h1": h1,
            "canonical": canonical,
            "robots": robots,
            "image_count": image_count,
            "images_missing_alt": images_missing_alt,
        }