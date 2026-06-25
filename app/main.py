# Import FastAPI
from fastapi import FastAPI

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