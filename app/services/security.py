"""
Security Headers Analysis Service.

Evaluates HTTP response headers and the final URL scheme for
security signals that Google considers when ranking HTTPS pages
and that protect users from common web attacks.
"""


def extract_security_data(response_headers: dict, final_url: str) -> dict:
    """
    Analyse HTTP response headers for key security signals.

    Parameters:
        response_headers: Dict of response headers from the initial page load
                          (keys may be any case — normalised internally).
        final_url:        Landing URL after all redirects (used for HTTPS check).

    Returns:
        dict with keys:
            is_https                  -- True if final_url uses https://
            has_hsts                  -- Strict-Transport-Security present
            has_x_frame_options       -- X-Frame-Options present
            has_csp                   -- Content-Security-Policy present
            has_x_content_type_options -- X-Content-Type-Options present
            hsts_value                -- raw header value or None
            x_frame_options_value     -- raw header value or None
            csp_value                 -- raw header value or None
    """
    # Normalise all header names to lowercase for consistent lookups
    headers = {k.lower(): v for k, v in (response_headers or {}).items()}

    return {
        "is_https":                   (final_url or "").startswith("https://"),
        "has_hsts":                   "strict-transport-security" in headers,
        "has_x_frame_options":        "x-frame-options" in headers,
        "has_csp":                    "content-security-policy" in headers,
        "has_x_content_type_options": "x-content-type-options" in headers,
        # Raw values — useful for AI analysis and display
        "hsts_value":             headers.get("strict-transport-security"),
        "x_frame_options_value":  headers.get("x-frame-options"),
        "csp_value":              headers.get("content-security-policy"),
    }
