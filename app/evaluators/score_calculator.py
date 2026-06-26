"""
SEO Score Calculator.

Converts a list of SEO issues (produced by seo_evaluator.py) into
a numeric score (0-100) and a letter grade (A-F).

Scoring weights:
    High severity   -15 points
    Medium severity  -7 points
    Low severity     -3 points
"""


def calculate_seo_score(issues: list) -> dict:
    """
    Calculate an overall SEO score from a list of detected issues.

    Parameters:
        issues: List of issue dicts from evaluate_seo(). Each dict
                must contain a "severity" key (High / Medium / Low).

    Returns:
        dict with keys: score (int 0-100), grade (str A/B/C/D/F).
    """
    score = 100  # start from a perfect score and deduct per issue

    for issue in issues:
        severity = issue.get("severity")
        if severity == "High":
            score -= 15
        elif severity == "Medium":
            score -= 7
        elif severity == "Low":
            score -= 3

    # Clamp score to zero -- multiple severe issues must not produce negative values
    score = max(score, 0)

    # Assign a letter grade based on standard academic thresholds
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return {"score": score, "grade": grade}
