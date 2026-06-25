# Import FastAPI
from fastapi import FastAPI

from fastapi.responses import JSONResponse
import json

class PrettyJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2
        ).encode("utf-8")

app = FastAPI(
title="SEO Audit Agent",
default_response_class=PrettyJSONResponse
)

# Import crawler service
from app.services.crawler import audit_page

# Create FastAPI application
app = FastAPI(title="SEO Audit Agent")


@app.get("/")
def home():
    """Health check endpoint."""
    return {"message": "SEO Audit Agent is running."}


@app.get("/audit")
def audit(url: str):
    """
    Audit a website URL and return SEO data.
    """
    return audit_page(url)