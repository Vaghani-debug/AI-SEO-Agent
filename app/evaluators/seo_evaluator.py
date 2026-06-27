"""
SEO Evaluation Engine.

Applies rule-based checks to the collected SEO data and returns
a list of issues. Each issue carries a severity, category,
description, and actionable recommendation.

Severity weights (applied by score_calculator.py):
    High   -15 pts  |  Medium  -7 pts  |  Low  -3 pts
"""


def evaluate_seo(data: dict) -> list:
    """
    Evaluate collected page data and generate a list of SEO issues.

    Parameters:
        data: Aggregated dict produced by the LangGraph extraction nodes.
              Expected keys: request, technical, metadata, heading_data,
              image_data, link_data.

    Returns:
        list[dict]: Detected issues, each with keys severity, category,
                    issue, and recommendation.
    """
    issues = []

    # ─── HTTP Status ─────────────────────────────────────────────────────────
    http_status = data["request"].get("http_status")
    if http_status != 200:
        issues.append({
            "severity": "High",
            "category": "Technical SEO",
            "issue": f"HTTP Status {http_status}",
            "recommendation": "Ensure the page returns HTTP 200.",
        })

    # ─── HTML Language Attribute ─────────────────────────────────────────────
    language = data["technical"].get("language")
    if not language:
        issues.append({
            "severity": "Low",
            "category": "Technical SEO",
            "issue": "Missing HTML language attribute",
            "recommendation": "Add a valid lang attribute to the <html> element (e.g. lang=\"en\").",
        })

    # ─── Mobile Viewport ─────────────────────────────────────────────────────
    viewport = data["technical"].get("viewport")
    if not viewport:
        issues.append({
            "severity": "High",
            "category": "Technical SEO",
            "issue": "Missing viewport meta tag",
            "recommendation": 'Add <meta name="viewport" content="width=device-width, initial-scale=1"> for mobile rendering.',
        })

    # ─── Character Encoding ──────────────────────────────────────────────────
    charset = data["technical"].get("charset")
    if not charset:
        issues.append({
            "severity": "Medium",
            "category": "Technical SEO",
            "issue": "Missing charset declaration",
            "recommendation": 'Add <meta charset="UTF-8"> as the first tag inside <head>.',
        })

    # ─── Open Graph Tags ─────────────────────────────────────────────────────
    technical = data["technical"]
    if not technical.get("og_title"):
        issues.append({
            "severity": "Medium",
            "category": "Social SEO",
            "issue": "Missing Open Graph title (og:title)",
            "recommendation": "Add <meta property=\"og:title\"> to control the title shown on social shares.",
        })
    if not technical.get("og_description"):
        issues.append({
            "severity": "Medium",
            "category": "Social SEO",
            "issue": "Missing Open Graph description (og:description)",
            "recommendation": "Add <meta property=\"og:description\"> to improve link previews on social platforms.",
        })
    if not technical.get("og_image"):
        issues.append({
            "severity": "Medium",
            "category": "Social SEO",
            "issue": "Missing Open Graph image (og:image)",
            "recommendation": "Add <meta property=\"og:image\"> with a 1200x630 px image for rich social previews.",
        })

    # ─── Twitter Card ────────────────────────────────────────────────────────
    if not technical.get("twitter_card"):
        issues.append({
            "severity": "Low",
            "category": "Social SEO",
            "issue": "Missing Twitter Card meta tag",
            "recommendation": 'Add <meta name="twitter:card" content="summary_large_image"> for richer X/Twitter shares.',
        })

    # ─── Page Title ──────────────────────────────────────────────────────────
    title = data["metadata"].get("title")
    if not title:
        issues.append({
            "severity": "High",
            "category": "Metadata",
            "issue": "Missing page title",
            "recommendation": "Add a unique, descriptive <title> tag to every page.",
        })
    else:
        title_length = len(title)
        if title_length < 30:
            issues.append({
                "severity": "Low",
                "category": "Metadata",
                "issue": f"Title too short ({title_length} chars)",
                "recommendation": "Keep the title between 30 and 60 characters for optimal SERP display.",
            })
        elif title_length > 60:
            issues.append({
                "severity": "Medium",
                "category": "Metadata",
                "issue": f"Title too long ({title_length} chars)",
                "recommendation": "Keep the title under 60 characters to avoid truncation in search results.",
            })

    # ─── Meta Description ────────────────────────────────────────────────────
    description = data["metadata"].get("meta_description")
    if not description:
        issues.append({
            "severity": "High",
            "category": "Metadata",
            "issue": "Missing meta description",
            "recommendation": "Add a unique meta description between 120 and 160 characters.",
        })
    else:
        description_length = len(description)
        if description_length < 120:
            issues.append({
                "severity": "Low",
                "category": "Metadata",
                "issue": f"Meta description too short ({description_length} chars)",
                "recommendation": "Aim for 120-160 characters to maximise SERP click-through rate.",
            })
        elif description_length > 160:
            issues.append({
                "severity": "Medium",
                "category": "Metadata",
                "issue": f"Meta description too long ({description_length} chars)",
                "recommendation": "Keep meta description under 160 characters to prevent truncation.",
            })

    # ─── Canonical URL ───────────────────────────────────────────────────────
    if not data["metadata"].get("canonical"):
        issues.append({
            "severity": "Medium",
            "category": "Technical SEO",
            "issue": "Missing canonical URL tag",
            "recommendation": "Add <link rel=\"canonical\"> to prevent duplicate content penalties.",
        })

    # ─── H1 Headings ─────────────────────────────────────────────────────────
    h1_count = data["heading_data"].get("h1_count", 0)
    if h1_count == 0:
        issues.append({
            "severity": "High",
            "category": "Headings",
            "issue": "Missing H1 heading",
            "recommendation": "Add exactly one H1 that describes the primary topic of the page.",
        })
    elif h1_count > 1:
        issues.append({
            "severity": "Medium",
            "category": "Headings",
            "issue": f"Multiple H1 headings ({h1_count} found)",
            "recommendation": "Use only one H1 per page; demote additional headings to H2.",
        })

    # ─── Image ALT Text ──────────────────────────────────────────────────────
    missing_alt = data["image_data"].get("images_missing_alt", 0)
    if missing_alt > 0:
        issues.append({
            "severity": "Medium",
            "category": "Images",
            "issue": f"{missing_alt} image(s) missing ALT text",
            "recommendation": "Add descriptive ALT text to every meaningful image for accessibility and image search.",
        })

    # ─── Internal Links ──────────────────────────────────────────────────────
    internal_links = data["link_data"].get("internal_links", 0)
    if internal_links == 0:
        issues.append({
            "severity": "High",
            "category": "Links",
            "issue": "No internal links found",
            "recommendation": "Add contextual internal links to distribute PageRank and help crawlers discover content.",
        })

    # ─── Structured Data (JSON-LD) ────────────────────────────────────────────
    if "structured_data" in data:
        sd = data["structured_data"]
        if not sd.get("has_structured_data"):
            issues.append({
                "severity": "Medium",
                "category": "Structured Data",
                "issue": "No structured data (JSON-LD) detected",
                "recommendation": (
                    "Add JSON-LD structured data (e.g. Organization, Article, "
                    "BreadcrumbList) to enable Rich Results in Google Search."
                ),
            })
        if sd.get("invalid_blocks", 0) > 0:
            issues.append({
                "severity": "Medium",
                "category": "Structured Data",
                "issue": f"{sd['invalid_blocks']} invalid JSON-LD block(s) detected",
                "recommendation": (
                    "Fix the malformed JSON-LD. Use Google's Rich Results Test "
                    "(search.google.com/test/rich-results) to validate."
                ),
            })

    # ─── Robots.txt and Sitemap ───────────────────────────────────────────────
    if "robots_data" in data:
        rb = data["robots_data"]
        if not rb.get("robots_accessible"):
            issues.append({
                "severity": "Medium",
                "category": "Crawlability",
                "issue": "robots.txt not accessible",
                "recommendation": (
                    "Create a robots.txt at the root of your domain to guide "
                    "search engine crawlers."
                ),
            })
        if rb.get("disallow_all"):
            issues.append({
                "severity": "High",
                "category": "Crawlability",
                "issue": "robots.txt blocks all search engine crawlers",
                "recommendation": (
                    "Remove or narrow the 'Disallow: /' rule under 'User-agent: *' "
                    "— it prevents Google from indexing your site."
                ),
            })
        if not rb.get("sitemap_accessible"):
            issues.append({
                "severity": "Medium",
                "category": "Crawlability",
                "issue": "XML sitemap not found or inaccessible",
                "recommendation": (
                    "Create an XML sitemap and submit it in Google Search Console "
                    "to help search engines discover all your pages."
                ),
            })

    # ─── Security Headers ────────────────────────────────────────────────────
    if "security" in data:
        sec = data["security"]
        if not sec.get("is_https"):
            issues.append({
                "severity": "High",
                "category": "Security",
                "issue": "Page not served over HTTPS",
                "recommendation": (
                    "Migrate to HTTPS. Google uses HTTPS as a ranking signal and "
                    "Chrome marks HTTP pages as 'Not Secure'."
                ),
            })
        if not sec.get("has_hsts"):
            issues.append({
                "severity": "Medium",
                "category": "Security",
                "issue": "Missing HSTS header (Strict-Transport-Security)",
                "recommendation": (
                    "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' "
                    "to enforce HTTPS for all future visits."
                ),
            })
        if not sec.get("has_x_frame_options"):
            issues.append({
                "severity": "Low",
                "category": "Security",
                "issue": "Missing X-Frame-Options header",
                "recommendation": "Add 'X-Frame-Options: SAMEORIGIN' to prevent clickjacking.",
            })
        if not sec.get("has_csp"):
            issues.append({
                "severity": "Medium",
                "category": "Security",
                "issue": "Missing Content-Security-Policy header",
                "recommendation": (
                    "Add a Content-Security-Policy header to restrict which "
                    "resources the browser may load, preventing XSS attacks."
                ),
            })
        if not sec.get("has_x_content_type_options"):
            issues.append({
                "severity": "Low",
                "category": "Security",
                "issue": "Missing X-Content-Type-Options header",
                "recommendation": "Add 'X-Content-Type-Options: nosniff' to prevent MIME sniffing.",
            })

    return issues
