from fastapi import FastAPI

app = FastAPI(title="SEO Audit Agent")

@app.get("/")
def root():
    return {"message": "SEO Audit Agent is running!"}