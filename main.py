from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import pandas as pd
import json
import os
import tempfile
from typing import Dict, List
import logging
from datetime import datetime

# Import your existing modules
from data_preprocessing import extract_bank_statement_table, clean_and_format_data, extract_transactions_regex
from batch_categorize_transactions import BatchTransactionCategorizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Transaction Tracker", description="Beautiful Transaction Analysis Tool")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# OpenAI API Key - Replace with your actual key or use environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Handle PDF upload and process transactions"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_pdf_path = temp_file.name
        
        logger.info(f"Processing PDF: {file.filename}")
        
        # Extract transactions from PDF
        try:
            df = extract_bank_statement_table(temp_pdf_path)
            df = clean_and_format_data(df)
            
            if df.empty:
                logger.info("First method failed, trying alternative approach...")
                df = extract_transactions_regex(temp_pdf_path)
                df = clean_and_format_data(df)
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            df = extract_transactions_regex(temp_pdf_path)
            df = clean_and_format_data(df)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="No transactions found in the PDF")
        
        # Clean up temp file
        os.unlink(temp_pdf_path)
        
        # Convert DataFrame to JSON format for categorization
        transactions_json = []
        for index, row in df.iterrows():
            transaction = {
                "id": index,
                "date": str(row.get('Date', '')),
                "narration": str(row.get('Narration', '')),
                "amount": float(row.get('Withdrawal(Dr)', 0)) if pd.notna(row.get('Withdrawal(Dr)')) and row.get('Withdrawal(Dr)') > 0 else float(row.get('Deposit(Cr)', 0)),
                "type": "debit" if pd.notna(row.get('Withdrawal(Dr)')) and row.get('Withdrawal(Dr)') > 0 else "credit"
            }
            transactions_json.append(transaction)
        
        # Initialize categorizer
        if OPENAI_API_KEY and OPENAI_API_KEY != "your-api-key-here":
            categorizer = BatchTransactionCategorizer(OPENAI_API_KEY, model_name="gpt-3.5-turbo")
            
            # Categorize transactions
            logger.info("Categorizing transactions...")
            categorization_results = categorizer.batch_categorize_all_transactions(
                transactions_json, 
                batch_size=20
            )
            
            # Add categories to DataFrame
            categories = []
            for index in range(len(df)):
                category = categorization_results.get(index, "Miscellaneous")
                categories.append(category)
            
            df['Category'] = categories
        else:
            # If no API key, assign default category
            df['Category'] = "Uncategorized"
            logger.warning("No OpenAI API key provided. Transactions will be uncategorized.")
        
        # Prepare response data
        transactions_data = df.to_dict('records')
        
        # Convert datetime objects to strings for JSON serialization
        for transaction in transactions_data:
            if 'Date' in transaction and pd.notna(transaction['Date']):
                transaction['Date'] = transaction['Date'].strftime('%Y-%m-%d') if hasattr(transaction['Date'], 'strftime') else str(transaction['Date'])
        
        # Calculate summary statistics
        total_transactions = len(df)
        total_withdrawals = df['Withdrawal(Dr)'].sum()
        total_deposits = df['Deposit(Cr)'].sum()
        date_range = {
            'start': df['Date'].min().strftime('%Y-%m-%d') if hasattr(df['Date'].min(), 'strftime') else str(df['Date'].min()),
            'end': df['Date'].max().strftime('%Y-%m-%d') if hasattr(df['Date'].max(), 'strftime') else str(df['Date'].max())
        }
        
        # Category distribution for pie chart
        if 'Category' in df.columns:
            category_counts = df['Category'].value_counts().to_dict()
        else:
            category_counts = {"Uncategorized": total_transactions}
        
        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "transactions": transactions_data,
            "summary": {
                "total_transactions": total_transactions,
                "total_withdrawals": float(total_withdrawals),
                "total_deposits": float(total_deposits),
                "date_range": date_range,
                "category_distribution": category_counts
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        # Clean up temp file if it exists
        if 'temp_pdf_path' in locals():
            try:
                os.unlink(temp_pdf_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)