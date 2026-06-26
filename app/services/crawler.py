"""
Web Crawler Service.

Responsibility: browser lifecycle ONLY.
  - Normalise the input URL
  - Launch a headless Playwright Chromium browser
  - Navigate to the target page
  - Return the live Playwright Page object plus request metadata

Everything else (extraction, evaluation, scoring, AI analysis,
and response building) belongs in the LangGraph workflow.
See app/agents/workflow.py for the full pipeline.
"""

import time

from playwright.sync_api import sync_playwright

from app.utils.helpers import normalize_url
from app.utils.logger import logger


def crawl_page(url: str) -> dict:
    """
    Open a headless browser and navigate to the given URL.

    Playwright is started with sync_playwright().start() (not as a
    context manager) so its lifecycle is owned by the caller.
    The caller (workflow aggregate_node) MUST release resources by
    calling state["browser"].close() and state["playwright_obj"].stop()
    after all extraction is complete.

    Parameters:
        url: Raw or normalized website URL.

    Returns:
        dict with keys:
            page           -- live Playwright Page object
            browser        -- Playwright Browser object (for cleanup)
            playwright_obj -- Playwright instance (for cleanup)
            status_code    -- HTTP response status code, or None
            final_url      -- URL after any redirects
            crawl_time     -- seconds taken to navigate (float)

    Raises:
        Exception: Any navigation failure; browser resources are cleaned
                   up before re-raising.
    """
    url = normalize_url(url)       # ensure scheme is present
    start_time = time.time()

    # Start Playwright outside a context manager so the caller controls shutdown
    pw = sync_playwright().start()

    try:
        # Headless Chromium is the most SEO-representative browser choice
        browser = pw.chromium.launch(headless=True)

        # Realistic User-Agent reduces the risk of bot-detection blocks
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.set_default_timeout(30000)  # cap all DOM operations at 30 s

        # Navigate and wait until the initial DOM is parsed (not full load)
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
        # Release browser resources before propagating so nothing leaks
        try:
            pw.stop()
        except Exception:
            pass
        logger.exception(f"Navigation failed for {url}")
        raise
