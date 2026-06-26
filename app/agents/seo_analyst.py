"""
AI SEO Analyst Agent.

Uses Google Gemini to provide intelligent SEO recommendations
beyond what rule-based checks can detect. Analyzes the raw SEO data
and issues list to produce prioritized, actionable guidance.
"""

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.utils.logger import logger


# System prompt that defines the AI agent's role and output format
SYSTEM_PROMPT = """You are an expert SEO consultant with 15+ years of experience.
You analyze website SEO data and provide actionable, prioritized recommendations.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation outside JSON.

Output format:
{
    "overall_assessment": "2-3 sentence summary of the website's SEO health",
    "priority_ranking": ["issue1 (most impactful)", "issue2", "issue3"],
    "detailed_recommendations": [
        {
            "issue": "issue name",
            "impact": "High/Medium/Low",
            "fix": "specific step-by-step fix",
            "effort": "Easy/Medium/Hard"
        }
    ],
    "content_suggestions": {
        "title": "suggested improved title (or null if current is good)",
        "meta_description": "suggested improved description (or null if current is good)"
    },
    "keyword_insights": ["observation about keywords or content gaps"]
}"""


def analyze_seo_with_ai(seo_data: dict, issues: list) -> dict | None:
    """
    Run AI-powered SEO analysis using Ollama LLM.

    Parameters:
        seo_data (dict): Raw extracted SEO data from all services.
        issues (list): Rule-based issues detected by seo_evaluator.

    Returns:
        dict: AI-generated analysis with recommendations, or None if LLM fails.
    """

    try:
        # Initialize Google Gemini LLM client
        # response_mime_type forces Gemini to return pure JSON with no surrounding text
        llm = ChatGoogleGenerativeAI(
            google_api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            temperature=settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
            response_mime_type="application/json",
        )

        # Build the human message with all SEO context
        human_content = _build_analysis_prompt(seo_data, issues)

        # Send to LLM and get response
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]

        logger.info("Sending SEO data to Gemini for AI analysis...")
        response = llm.invoke(messages)

        # Parse the JSON response from LLM
        result = _parse_llm_response(response.content)

        logger.info("AI analysis completed successfully.")
        return result

    except Exception as e:
        logger.warning(f"AI analysis failed: {e}")
        return None


def _build_analysis_prompt(seo_data: dict, issues: list) -> str:
    """
    Build the analysis prompt with all SEO context for the LLM.

    Parameters:
        seo_data (dict): Raw SEO data from crawl.
        issues (list): Detected SEO issues.

    Returns:
        str: Formatted prompt string.
    """

    # Extract key information for the prompt
    metadata = seo_data.get("metadata", {})
    heading_data = seo_data.get("heading_data", {})
    image_data = seo_data.get("image_data", {})
    link_data = seo_data.get("link_data", {})
    technical = seo_data.get("technical", {})

    prompt = f"""Analyze this website's SEO data and provide recommendations.

## Current SEO Data

**Page Title:** {metadata.get("title", "MISSING")}
**Meta Description:** {metadata.get("meta_description", "MISSING")}
**Canonical URL:** {metadata.get("canonical", "MISSING")}
**HTML Language:** {technical.get("language", "MISSING")}
**Viewport:** {technical.get("viewport", "MISSING")}
**Charset:** {technical.get("charset", "MISSING")}

## Headings
- H1 Count: {heading_data.get("h1_count", 0)}
- H1 Text: {heading_data.get("h1", "MISSING")}
- H2 Count: {heading_data.get("h2_count", 0)}
- H3 Count: {heading_data.get("h3_count", 0)}

## Images
- Total Images: {image_data.get("total_images", 0)}
- Missing ALT: {image_data.get("images_missing_alt", 0)}

## Links
- Internal Links: {link_data.get("internal_links", 0)}
- External Links: {link_data.get("external_links", 0)}

## Open Graph & Social
- OG Title: {technical.get("og_title", "MISSING")}
- OG Description: {technical.get("og_description", "MISSING")}
- OG Image: {technical.get("og_image", "MISSING")}
- Twitter Card: {technical.get("twitter_card", "MISSING")}

## Detected Issues ({len(issues)} total)
"""

    # Add each issue to the prompt
    for i, issue in enumerate(issues, 1):
        prompt += f"{i}. [{issue['severity']}] {issue['issue']} - {issue['recommendation']}\n"

    prompt += "\nProvide your analysis as JSON."

    return prompt


def _parse_llm_response(content: str) -> dict | None:
    """
    Parse the LLM response string into a structured dict.
    Handles cases where LLM wraps JSON in markdown code blocks.

    Parameters:
        content (str): Raw LLM response text.

    Returns:
        dict: Parsed analysis, or None if parsing fails.
    """

    # Strip markdown code fences if present
    text = content.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # First attempt: parse the full text directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second attempt: extract JSON by finding the outermost { ... } block.
    # Handles cases where Gemini adds explanatory text before or after the JSON.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    # Final fallback: return structured error so the response stays valid
    logger.warning("Failed to parse AI response as JSON after all attempts.")
    return {
            "overall_assessment": text[:500],
            "priority_ranking": [],
            "detailed_recommendations": [],
            "content_suggestions": {},
            "keyword_insights": ["AI response could not be parsed as structured JSON."]
        }
