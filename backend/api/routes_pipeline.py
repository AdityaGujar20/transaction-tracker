from fastapi import APIRouter, UploadFile, File

import shutil
from pathlib import Path

from core.table_extractor import extract_pdf_to_json
from core.categorizer import categorize_transactions_json

router = APIRouter()

@router.post("/run-pipeline")
def run_pipeline(pdf: UploadFile = File(...)):
    # Setup directories
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded PDF
    pdf_path = raw_dir / pdf.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf.file, buffer)

    # Step 1: Extract table from PDF
    transactions_json = extract_pdf_to_json(str(pdf_path))

    # Step 2: Categorize transactions
    categorize_transactions_json(transactions_json, str(processed_dir))

    return {"message": "Pipeline completed"}