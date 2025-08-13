from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from api import routes_pipeline, faq, chatbot_routes
from pathlib import Path
import shutil
import os
import time
from starlette.responses import Response as StarletteResponse

app = FastAPI(
    title="Transaction Tracker APIs",
    description="Extracts, categorizes, and analyzes bank statements",
    version="1.0"
)

# Custom StaticFiles class with cache control
class NoCacheStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs) -> StarletteResponse:
        response = super().file_response(*args, **kwargs)
        # Add cache control headers for development
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# Serve static files (CSS, JS, images) with no-cache headers
app.mount("/static", NoCacheStaticFiles(directory="../frontend/static"), name="static")

# HTML templates
templates = Jinja2Templates(directory="../frontend/templates")

# Register API routes
app.include_router(routes_pipeline.router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(faq.router, prefix="/faq", tags=["Financial Analysis"])
app.include_router(chatbot_routes.router, prefix="/chatbot", tags=["Chatbot"])

# Home page (HTML)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Add timestamp for cache busting
    timestamp = str(int(time.time()))
    response = templates.TemplateResponse("index.html", {
        "request": request, 
        "timestamp": timestamp
    })
    # Add cache control headers for development
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Dashboard page (HTML)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Add timestamp for cache busting
    timestamp = str(int(time.time()))
    response = templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "timestamp": timestamp
    })
    # Add cache control headers for development
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Chatbot page (HTML)
@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot_page(request: Request):
    # Add timestamp for cache busting
    timestamp = str(int(time.time()))
    response = templates.TemplateResponse("chatbot.html", {
        "request": request, 
        "timestamp": timestamp
    })
    # Add cache control headers for development
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Serve the JSON data for dashboard
@app.get("/data/processed/categorized_transactions.json")
async def get_transaction_data():
    # Use absolute path or relative to backend directory
    json_file_path = Path("data/processed/categorized_transactions.json")
    
    # If not found, try relative to backend directory
    if not json_file_path.exists():
        json_file_path = Path("backend/data/processed/categorized_transactions.json")
    
    if not json_file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction data not found. Please upload and process your bank statement first.")
    
    # Add cache control headers to prevent caching
    response = FileResponse(json_file_path, media_type="application/json")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# API root JSON
@app.get("/api-info")
def api_info():
    return {
        "message": "Welcome to the Transaction Tracker API",
        "version": "1.0",
        "available_endpoints": {
            "pages": {
                "home": "/",
                "dashboard": "/dashboard",
                "chatbot": "/chatbot"
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
            "chatbot": {
                "chat": "/chatbot/chat",
                "stats": "/chatbot/stats",
                "health": "/chatbot/health"
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