# SEO Audit Agent

AI-powered SEO audit API built with **FastAPI**, **LangGraph**, and **Google Gemini**.
Crawls any URL with a headless Chromium browser and returns a structured JSON report
covering metadata, headings, images, links, technical signals, structured data,
crawlability, security headers, a numeric score, and optional AI recommendations.

---

## Requirements

- Python 3.11 or higher
- A Google Gemini API key (only required when using `ai=true`)

---

## Installation

1. Clone the repository

   `ash
   git clone https://github.com/Vaghani-debug/AI-SEO-Agent.git
   cd AI-SEO-Agent
   `

2. Create and activate a virtual environment

   `ash
   python -m venv venv
   venv\Scriptsctivate        # Windows
   # source venv/bin/activate   # macOS / Linux
   `

3. Install Python dependencies

   `ash
   pip install -r requirements.txt
   `

4. Install the Playwright browser binary

   `ash
   playwright install chromium
   `

---

## Configuration

Create a .env file in the project root:

`env
# Required for AI analysis
GEMINI_API_KEY=your_api_key_here

# Optional - Gemini tuning
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.3
GEMINI_MAX_TOKENS=2048

# Optional - crawler behaviour
CRAWLER_TIMEOUT_MS=30000
CRAWLER_MAX_ATTEMPTS=2

# Optional - result cache
AUDIT_CACHE_ENABLED=true
AUDIT_CACHE_TTL_SECONDS=3600

# Optional - logging
LOG_LEVEL=INFO
`

---

## Running the server

`ash
uvicorn app.main:app --reload
`

The API is available at **http://localhost:8000**.

---

## API Reference

### GET /

HTML landing page confirming the service is running.

### GET /audit

Run a full SEO audit on any URL.

| Parameter | Type    | Default      | Description                                  |
|-----------|---------|--------------|----------------------------------------------|
| url     | string  | **required** | Website URL to audit (https:// optional)   |
| i      | boolean | alse      | Include AI-powered analysis via Google Gemini|

Example:

`ash
curl http://localhost:8000/audit?url=https://example.com
`

---

## Running Tests

`ash
python -m pytest tests/ -v
`

All tests use mock Playwright objects - no real browser is launched by the test suite.

---

## Architecture

The audit runs through a **14-node sequential LangGraph pipeline**:

`
crawl
  | (failure -> aggregate)
metadata -> headings -> images -> links -> technical
  |
structured_data -> robots -> security
  |
validate
  | (failure -> aggregate)
evaluate -> scoring -> [ai_analyze] -> aggregate -> END
`

Each extraction node owns one SEO dimension and fails independently.
Results for successful audits are cached in memory (configurable TTL).

### Scoring

| Severity | Point deduction |
|----------|----------------|
| High     | -15 pts        |
| Medium   | -7 pts         |
| Low      | -3 pts         |

Grades: A >= 90, B >= 80, C >= 70, D >= 60, F < 60