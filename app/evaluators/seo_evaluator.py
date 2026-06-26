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

    return issues
