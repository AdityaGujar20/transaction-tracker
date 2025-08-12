from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from api import routes_pipeline, faq
from pathlib import Path
import shutil
import os

app = FastAPI(
    title="Transaction Tracker APIs",
    description="Extracts, categorizes, and analyzes bank statements",
    version="1.0"
)

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# HTML templates
templates = Jinja2Templates(directory="../frontend/templates")

# Register API routes
app.include_router(routes_pipeline.router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(faq.router, prefix="/faq", tags=["Financial Analysis"])

# Home page (HTML)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Dashboard page (HTML)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Serve the JSON data for dashboard
@app.get("/data/processed/categorized_transactions.json")
async def get_transaction_data():
    json_file_path = Path("data/processed/categorized_transactions.json")
    
    if not json_file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction data not found. Please upload and process your bank statement first.")
    
    return FileResponse(json_file_path, media_type="application/json")

# API root JSON
@app.get("/api-info")
def api_info():
    return {
        "message": "Welcome to the Transaction Tracker API",
        "version": "1.0",
        "available_endpoints": {
            "pages": {
                "home": "/",
                "dashboard": "/dashboard"
            },
            "pipeline": {
                "run_pipeline": "/pipeline/run-pipeline"
            },
            "financial_analysis": {
                "complete_analysis": "/faq/get-answers",
                "total_spending": "/faq/total-spending", 
                "total_income": "/faq/total-income",
                "highest_expense": "/faq/highest-expense",
                "highest_category": "/faq/highest-category",
                "category_spending": "/faq/category-spending",
                "financial_summary": "/faq/summary"
            },
            "data": {
                "transaction_data": "/data/processed/categorized_transactions.json"
            },
            "documentation": "/docs"
        }
    }

# Deletes the files inside data/processed
@app.delete("/refresh-data")
def refresh_data():
    processed_dir = Path("data/processed")

    if processed_dir.exists() and processed_dir.is_dir():
        shutil.rmtree(processed_dir)  # delete folder
        processed_dir.mkdir(parents=True, exist_ok=True)  # recreate empty folder
    
    return {"message": "Processed data cleared successfully"}