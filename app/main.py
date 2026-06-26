import json
import re
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.services.crawler import audit_page


class PrettyJSONResponse(JSONResponse):
        def render(self, content) -> bytes:
                return json.dumps(
                        content,
                        ensure_ascii=False,
                        allow_nan=False,
                        indent=2,
                ).encode("utf-8")


app = FastAPI(
        title="SEO Audit Agent",
        default_response_class=PrettyJSONResponse,
)


@app.get("/", response_class=HTMLResponse)
def home():
        return """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>SEO Audit Agent</title>
            <style>
                :root {
                    --bg-1: #f8fbff;
                    --bg-2: #e9f2ff;
                    --card: #ffffff;
                    --ink: #0f172a;
                    --muted: #475569;
                    --brand: #0b5ed7;
                    --brand-dark: #084298;
                    --line: #dbeafe;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    background: radial-gradient(circle at 20% 20%, #ffffff 0%, var(--bg-1) 40%, var(--bg-2) 100%);
                    font-family: "Segoe UI", "Trebuchet MS", sans-serif;
                    color: var(--ink);
                    padding: 24px;
                }
                .card {
                    width: min(820px, 100%);
                    background: var(--card);
                    border: 1px solid var(--line);
                    border-radius: 18px;
                    box-shadow: 0 14px 40px rgba(11, 66, 152, 0.12);
                    overflow: hidden;
                }
                .hero {
                    padding: 28px 28px 12px 28px;
                    background: linear-gradient(135deg, #ffffff 0%, #f2f7ff 100%);
                }
                h1 {
                    margin: 0 0 8px 0;
                    font-size: clamp(1.5rem, 3vw, 2rem);
                    letter-spacing: 0.2px;
                    color: var(--brand-dark);
                }
                p {
                    margin: 0;
                    color: var(--muted);
                    line-height: 1.6;
                }
                .body {
                    padding: 18px 28px 28px 28px;
                    display: grid;
                    gap: 14px;
                }
                .endpoint {
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                    padding: 12px;
                    font-family: Consolas, "Courier New", monospace;
                    word-break: break-all;
                    color: #0f172a;
                }
                .actions {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                }
                a.button {
                    text-decoration: none;
                    border: 1px solid var(--brand);
                    color: var(--brand);
                    padding: 10px 14px;
                    border-radius: 10px;
                    font-weight: 600;
                    transition: all 0.2s ease;
                }
                a.button:hover {
                    background: var(--brand);
                    color: #fff;
                }
            </style>
        </head>
        <body>
            <main class="card">
                <section class="hero">
                    <h1>SEO Audit Agent</h1>
                    <p>Service is running and ready to analyze a page URL.</p>
                </section>
                <section class="body">
                    <div class="endpoint">GET /audit?url=https://example.com</div>
                    <div class="actions">
                        <a class="button" href="/docs">Open API Docs</a>
                        <a class="button" href="/openapi.json">View OpenAPI JSON</a>
                    </div>
                </section>
            </main>
        </body>
        </html>
        """


@app.get("/audit")
def audit(
        url: str = Query(..., description="Website URL to audit"),
        ai: Optional[bool] = Query(False, description="Enable AI-powered analysis via Ollama")
):
        # Validate URL format before processing
        url_pattern = re.compile(
                r'^https?://[^\s/$.?#].[^\s]*$',
                re.IGNORECASE
        )
        # Also accept URLs without scheme (will be normalized later)
        bare_pattern = re.compile(
                r'^[a-zA-Z0-9][a-zA-Z0-9-]*(\.[a-zA-Z]{2,})+',
                re.IGNORECASE
        )

        if not url_pattern.match(url) and not bare_pattern.match(url):
                return {
                        "success": False,
                        "message": "Invalid URL format. Provide a valid website URL.",
                        "url": url
                }

        return audit_page(url, enable_ai=ai)