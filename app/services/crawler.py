# Import required modules
import time
from app.services.metadata import extract_metadata
from app.services.images import extract_images
from app.services.headings import extract_headings

# Import Playwright synchronous API
from playwright.sync_api import sync_playwright

# Import helper functions
from app.utils.helpers import normalize_url, safe_attribute, safe_text

# Import application logger
from app.utils.logger import logger


def audit_page(url: str):
    """
    Crawl a webpage and collect basic SEO information.

    Parameters:
        url (str): Website URL entered by the user.

    Returns:
        dict: Structured SEO audit response.
    """

    # Normalize the URL (adds https:// if missing)
    url = normalize_url(url)

    # Record crawl start time
    start_time = time.time()

    try:

        # Start Playwright
        with sync_playwright() as p:

            # Launch Chromium browser in headless mode
            browser = p.chromium.launch(headless=True)

            # Create browser context
            # Custom User-Agent reduces the chance of websites blocking Playwright
            context = browser.new_context(
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0 Safari/537.36"
                )
            )

            # Open a new browser page
            page = context.new_page()

            # Set maximum wait time for all Playwright operations
            page.set_default_timeout(30000)

            # -------------------------
            # Navigate to the website
            # -------------------------

            try:

                # Load the webpage
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

            except Exception:

                logger.exception(f"Navigation failed for {url}")

                return {
                    "success": False,
                    "message": "Website could not be reached.",
                    "url": url
                }

            # -------------------------
            # Collect crawl information
            # -------------------------

            # HTTP status code (200, 301, 404, etc.)
            status_code = response.status if response else None

            # Final URL after redirects
            final_url = page.url

            # Calculate crawl duration
            crawl_time = round(time.time() - start_time, 2)

            # -------------------------
            # Basic SEO Information
            # -------------------------
            # Extract metadata using the metadata service
            metadata = extract_metadata(page)
            # Extract heading information using the headings service
            heading_data = extract_headings(page)
                    
            # -------------------------
            # Image SEO
            # -------------------------
            # Extract image SEO information using the images service
            image_data = extract_images(page)

            image_count = image_data.get("image_count", 0)

            # -------------------------
            # Write successful crawl to log
            # -------------------------

            logger.info(
                f"SEO Audit Completed | "
                f"URL={url} | "
                f"Status={status_code} | "
                f"Time={crawl_time}s"
            )

            # -------------------------
            # Return structured response
            # -------------------------

            return {

                "success": True,

                "message": "SEO audit completed successfully.",

                "execution_time": crawl_time,

                "data": {

                    "url": url,

                    "final_url": final_url,

                    "http_status": status_code,

                    "metadata": metadata,

                    "heading_data": heading_data,

                    "image_data": image_data

                }

            }

    except Exception as e:

        # Log unexpected errors with full traceback
        logger.exception(f"SEO audit failed for {url}")

        return {

            "success": False,

            "message": "Unexpected error during SEO audit.",

            "url": url,

            "error": str(e)

        }