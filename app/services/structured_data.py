"""
Structured Data Extraction Service.

Detects and validates JSON-LD blocks embedded in
<script type="application/ld+json"> elements.  Structured data
enables Rich Results in Google Search and is an increasingly
important SEO signal.
"""

import json


def extract_structured_data(page) -> dict:
    """
    Find all JSON-LD <script> blocks, parse them, and report schema types.

    Parameters:
        page: Playwright page object (must already be navigated).

    Returns:
        dict with keys:
            has_structured_data  -- True if at least one valid block found
            schema_types         -- list of @type values from valid blocks
            total_blocks         -- raw count of script[type=application/ld+json]
            valid_blocks         -- count that parsed successfully as JSON
            invalid_blocks       -- count that failed JSON parsing
    """
    scripts = page.locator("script[type='application/ld+json']")
    total_blocks = scripts.count()

    schema_types: list[str] = []
    valid_blocks  = 0
    invalid_blocks = 0

    for i in range(total_blocks):
        try:
            text = scripts.nth(i).text_content()
            if not text or not text.strip():
                invalid_blocks += 1
                continue

            data = json.loads(text.strip())

            # Blocks may be a single object or an array of objects
            items = data if isinstance(data, list) else [data]
            for item in items:
                schema_type = item.get("@type")
                if schema_type:
                    # @type can itself be a list in some schemas
                    if isinstance(schema_type, list):
                        schema_types.extend(schema_type)
                    else:
                        schema_types.append(schema_type)

            valid_blocks += 1

        except (json.JSONDecodeError, Exception):
            invalid_blocks += 1

    return {
        "has_structured_data": valid_blocks > 0,
        "schema_types":        schema_types,
        "total_blocks":        total_blocks,
        "valid_blocks":        valid_blocks,
        "invalid_blocks":      invalid_blocks,
    }
