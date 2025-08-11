from fastapi import APIRouter, UploadFile, File
import shutil
from pathlib import Path
from core.table_extractor import extract_pdf_to_csv
from core.categorizer import categorize_transactions

router = APIRouter()

@router.post("/run-pipeline")
def run_pipeline(pdf: UploadFile = File(...)):
    raw_dir = Path("../data/raw")
    processed_dir = Path("../data/processed")

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded PDF
    pdf_path = raw_dir / pdf.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf.file, buffer)

    csv_path = processed_dir / "bank_transactions.csv"
    categorized_csv_path = processed_dir / "categorized_bank_transactions.csv"

    # Step 1: Extract table
    extract_pdf_to_csv(str(pdf_path), str(csv_path))

    # Step 2: Categorize
    categorize_transactions(str(csv_path), str(categorized_csv_path))

    return {
        "message": "Pipeline complete"
    }