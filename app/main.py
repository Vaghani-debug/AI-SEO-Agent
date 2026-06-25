from fastapi import FastAPI
from app.services.crawler import get_page_title

app = FastAPI(title="SEO Audit Agent")


@app.get("/")
def root():
    return {"message": "SEO Audit Agent is running!"}


@app.get("/crawl")
def crawl(url: str):
    title = get_page_title(url)

    return {
        "url": url,
        "title": title
    }