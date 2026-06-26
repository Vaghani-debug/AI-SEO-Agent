# Web Crawler Service
#
# Responsibility: browser lifecycle ONLY.
#   - Normalize URL
#   - Launch Playwright browser
#   - Navigate to the page
#   - Return the live page object + request metadata
#
# Everything else (extraction, evaluation, scoring, AI, response building)
# belongs in the LangGraph workflow — see app/agents/workflow.py

import time

# Import Playwright synchronous API
from playwright.sync_api import sync_playwright

# Import helper functions
from app.utils.helpers import normalize_url

# Import application logger
from app.utils.logger import logger


def crawl_page(url: str) -> dict:
    """
    Open a browser and navigate to the given URL.

    This function is responsible ONLY for the browser lifecycle.
    It does NOT extract, evaluate, score, or call AI.

    The caller (workflow aggregate_node) MUST close browser and playwright
    by calling state["browser"].close() and state["playwright_obj"].stop()
    when processing is complete.

    Parameters:
        url (str): Raw or normalized website URL.

    Returns:
        dict: {
            "page"           : Playwright Page object (live),
            "browser"        : Playwright Browser object,
            "playwright_obj" : Playwright instance (for cleanup),
            "status_code"    : int | None,
            "final_url"      : str,
            "crawl_time"     : float,
        }

    Raises:
        Exception: If navigation fails — caller handles gracefully.
    """

    # Normalize URL — adds https:// if scheme is missing
    url = normalize_url(url)

    # Record when the crawl started
    start_time = time.time()

    # Start Playwright without a context manager so its lifecycle
    # is controlled by the workflow (not this function)
    pw = sync_playwright().start()

    try:
        # Launch Chromium in headless mode
        browser = pw.chromium.launch(headless=True)

        # Create browser context with a realistic User-Agent to avoid blocks
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0 Safari/537.36"
            )
        )

        # Open a new tab
        page = context.new_page()

        # Cap all Playwright operations at 30 seconds
        page.set_default_timeout(30000)

        # Navigate to the URL and wait for the DOM to be ready
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)

        status_code = response.status if response else None
        final_url   = page.url
        crawl_time  = round(time.time() - start_time, 2)

        logger.info(f"Crawl OK | URL={url} | Status={status_code} | Time={crawl_time}s")

        return {
            "page":           page,
            "browser":        browser,
            "playwright_obj": pw,
            "status_code":    status_code,
            "final_url":      final_url,
            "crawl_time":     crawl_time,
        }

    except Exception:
        # Clean up browser resources before propagating the error
        try:
            pw.stop()
        except Exception:
            pass
        logger.exception(f"Navigation failed for {url}")
        raise
