from playwright.sync_api import sync_playwright


def get_page_title(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(url, wait_until="networkidle")

        title = page.title()

        browser.close()

        return title