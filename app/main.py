from fastapi import FastAPI
from app.services.crawler import audit_page

app = FastAPI(title="SEO Audit Agent")


@app.get("/")
def root():
    return {"message": "SEO Audit Agent is running!"}


@app.get("/audit")
def audit(url: str):
    return audit_page(url)