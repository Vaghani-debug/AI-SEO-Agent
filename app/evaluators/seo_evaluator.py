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

    metadata = data.get("metadata", {}) or {}
    heading_data = data.get("heading_data", {}) or {}
    image_data = data.get("image_data", {}) or {}

    meta_description = metadata.get("meta_description")
    h1_count = heading_data.get("h1_count") or 0
    images_missing_alt = image_data.get("images_missing_alt") or 0

    if not meta_description:
        issues.append({
            "severity": "High",
            "category": "Metadata",
            "issue": "Missing Meta Description",
            "recommendation": "Add a unique meta description."
        })

    if h1_count == 0:
        issues.append({
            "severity": "High",
            "category": "Headings",
            "issue": "Missing H1",
            "recommendation": "Add one H1 heading."
        })
    elif h1_count > 1:
        issues.append({
            "severity": "Medium",
            "category": "Headings",
            "issue": "Multiple H1 headings",
            "recommendation": "Keep only one H1."
        })

    if images_missing_alt > 0:
        issues.append({
            "severity": "Medium",
            "category": "Images",
            "issue": "Images missing ALT text",
            "recommendation": "Add ALT text to all images."
        })

    return issues