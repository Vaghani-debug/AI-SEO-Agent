"""
Robots.txt and Sitemap Discovery Service.

Fetches /robots.txt from the target domain, parses crawl directives,
and verifies the XML sitemap is accessible.  These are foundational
crawlability signals that affect whether search engines index the site.
"""

import httpx
from urllib.parse import urlparse


_TIMEOUT = 10          # seconds per request
_USER_AGENT = "Mozilla/5.0 (compatible; SEOAuditBot/1.0)"


def fetch_robots_data(url: str) -> dict:
    """
    Fetch robots.txt and check sitemap accessibility for the given URL's domain.

    Parameters:
        url: Any URL on the target site (scheme + domain extracted automatically).

    Returns:
        dict with keys:
            robots_accessible  -- True if /robots.txt returned HTTP 200
            robots_url         -- absolute URL of the robots.txt that was checked
            disallow_all       -- True if wildcard User-agent is fully blocked
            sitemap_url        -- sitemap URL found in robots.txt, or /sitemap.xml fallback
            sitemap_accessible -- True if the sitemap URL returned HTTP 200
    """
    parsed   = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{base_url}/robots.txt"

    result = {
        "robots_accessible":  False,
        "robots_url":         robots_url,
        "disallow_all":       False,
        "sitemap_url":        None,
        "sitemap_accessible": False,
    }

    # ── Fetch robots.txt ─────────────────────────────────────────────────────
    try:
        resp = httpx.get(
            robots_url,
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        if resp.status_code == 200:
            result["robots_accessible"] = True
            _parse_robots(resp.text, result)
    except Exception:
        pass   # network error — leave accessible=False

    # ── Sitemap fallback if not declared in robots.txt ────────────────────────
    if not result["sitemap_url"]:
        result["sitemap_url"] = f"{base_url}/sitemap.xml"

    # ── Check sitemap accessibility ──────────────────────────────────────────
    try:
        sitemap_resp = httpx.head(
            result["sitemap_url"],
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        result["sitemap_accessible"] = sitemap_resp.status_code == 200
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_robots(content: str, result: dict) -> None:
    """
    Parse robots.txt content in-place, updating result dict.

    Extracts the first Sitemap directive and detects a wildcard full-disallow.
    """
    current_ua: str | None = None
    wildcard_disallows: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()

        # Skip blank lines and comments
        if not line or line.startswith("#"):
            continue

        lower = line.lower()

        if lower.startswith("user-agent:"):
            current_ua = line.split(":", 1)[1].strip()

        elif lower.startswith("disallow:") and current_ua == "*":
            path = line.split(":", 1)[1].strip()
            wildcard_disallows.append(path)

        elif lower.startswith("sitemap:") and not result["sitemap_url"]:
            sitemap_raw = line.split(":", 1)[1].strip()
            # Re-attach the scheme that was split off if it started with http(s)
            # e.g. "Sitemap: https://..." → split gives "//..."  so we prepend scheme
            if sitemap_raw.startswith("//"):
                sitemap_raw = "https:" + sitemap_raw
            result["sitemap_url"] = sitemap_raw

    # "/" alone means block everything under root
    result["disallow_all"] = "/" in wildcard_disallows
