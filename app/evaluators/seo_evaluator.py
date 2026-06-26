"""
SEO Evaluation Engine.

Converts collected SEO data into SEO issues.
"""


def evaluate_seo(data):
    """
    Evaluate collected SEO data.

    Parameters:
        data (dict)

    Returns:
        list
    """

    issues = []

    # -----------------------------------
    # HTTP Status
    # -----------------------------------

    http_status = data["request"].get("http_status")

    # Check whether the page returned HTTP 200
    if http_status != 200:

        issues.append({

            "severity": "High",

            "category": "Technical SEO",

            "issue": f"HTTP Status {http_status}",

            "recommendation": "Ensure the page returns HTTP 200."

        })

    # -----------------------------------
    # HTML Language
    # -----------------------------------

    language = data["technical"].get("language")

    if not language:

        issues.append({

            "severity": "Low",

            "category": "Technical SEO",

            "issue": "Missing HTML language attribute",

            "recommendation": "Add a valid lang attribute to the <html> element."

        })

    # -----------------------------------
    # Mobile Viewport
    # -----------------------------------

    viewport = data["technical"].get("viewport")

    if not viewport:

        issues.append({

            "severity": "High",

            "category": "Technical SEO",

            "issue": "Missing viewport meta tag",

            "recommendation": "Add a responsive viewport meta tag."

        })

    # -----------------------------------
    # Charset
    # -----------------------------------

    charset = data["technical"].get("charset")

    if not charset:

        issues.append({

            "severity": "Medium",

            "category": "Technical SEO",

            "issue": "Missing charset declaration",

            "recommendation": "Declare UTF-8 charset."

        })

    # -----------------------------------
    # Open Graph
    # -----------------------------------

    technical = data["technical"]

    if not technical.get("og_title"):

        issues.append({

            "severity": "Medium",

            "category": "Social SEO",

            "issue": "Missing Open Graph title",

            "recommendation": "Add og:title."

        })

    if not technical.get("og_description"):

        issues.append({

            "severity": "Medium",

            "category": "Social SEO",

            "issue": "Missing Open Graph description",

            "recommendation": "Add og:description."

        })

    if not technical.get("og_image"):

        issues.append({

            "severity": "Medium",

            "category": "Social SEO",

            "issue": "Missing Open Graph image",

            "recommendation": "Add og:image."

        })

    # -----------------------------------
    # Twitter Card
    # -----------------------------------

    if not technical.get("twitter_card"):

        issues.append({

            "severity": "Low",

            "category": "Social SEO",

            "issue": "Missing Twitter Card",

            "recommendation": "Add twitter:card meta tag."

        })

    # -----------------------------------
    # Page Title
    # -----------------------------------

    title = data["metadata"].get("title")

    if not title:

        issues.append({

            "severity": "High",

            "category": "Metadata",

            "issue": "Missing Title",

            "recommendation": "Add a unique page title."

        })

    else:

        title_length = len(title)

        if title_length < 30:

            issues.append({

                "severity": "Low",

                "category": "Metadata",

                "issue": "Title is too short",

                "recommendation": "Keep title between 30–60 characters."

            })

        elif title_length > 60:

            issues.append({

                "severity": "Medium",

                "category": "Metadata",

                "issue": "Title is too long",

                "recommendation": "Keep title below 60 characters."

            })

    # -----------------------------------
    # Meta Description
    # -----------------------------------

    description = data["metadata"].get("meta_description")

    if not description:

        issues.append({

            "severity": "High",

            "category": "Metadata",

            "issue": "Missing Meta Description",

            "recommendation": "Add a unique meta description."

        })

    else:

        description_length = len(description)

        if description_length < 120:

            issues.append({

                "severity": "Low",

                "category": "Metadata",

                "issue": "Meta description is too short",

                "recommendation": "Aim for 120–160 characters."

            })

        elif description_length > 160:

            issues.append({

                "severity": "Medium",

                "category": "Metadata",

                "issue": "Meta description is too long",

                "recommendation": "Keep it under 160 characters."

            })

    # -----------------------------------
    # Canonical
    # -----------------------------------

    if not data["metadata"].get("canonical"):

        issues.append({

            "severity": "Medium",

            "category": "Technical SEO",

            "issue": "Missing Canonical URL",

            "recommendation": "Add a canonical tag."

        })

    # -----------------------------------
    # Headings
    # -----------------------------------

    h1_count = data["heading_data"].get("h1_count")

    if h1_count == 0:

        issues.append({

            "severity": "High",

            "category": "Headings",

            "issue": "Missing H1",

            "recommendation": "Add exactly one H1."

        })

    elif h1_count > 1:

        issues.append({

            "severity": "Medium",

            "category": "Headings",

            "issue": "Multiple H1 headings",

            "recommendation": "Keep only one H1."

        })

    # -----------------------------------
    # Images
    # -----------------------------------

    missing_alt = data["image_data"].get("images_missing_alt", 0)

    if missing_alt > 0:

        issues.append({

            "severity": "Medium",

            "category": "Images",

            "issue": f"{missing_alt} images missing ALT text",

            "recommendation": "Add ALT text to every important image."

        })

    # -----------------------------------
    # Internal Links
    # -----------------------------------

    internal_links = data["link_data"].get("internal_links", 0)

    if internal_links == 0:

        issues.append({

            "severity": "High",

            "category": "Links",

            "issue": "No internal links found",

            "recommendation": "Add internal links between relevant pages."

        })

    return issues