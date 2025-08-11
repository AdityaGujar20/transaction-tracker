from fastapi import FastAPI
from api import routes_pipeline

app = FastAPI(
    title="Transaction Tracker APIs",
    description="Extracts, categorizes, and analyzes bank statements",
    version="1.0"
)

# Register API routes
app.include_router(routes_pipeline.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Transaction Tracker API"}