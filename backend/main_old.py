from core.table_extractor import extract_pdf_to_csv
from core.categorizer import categorize_transactions

pdf_path = "data/raw/kotak-bankstatement-1y-1-4.pdf"
csv_path = "data/processed/bank_transactions.csv"
categorized_csv_path = "data/processed/categorized_bank_transactions.csv"

# Step 1: Extract table from PDF
extract_pdf_to_csv(pdf_path, csv_path)

# Step 2: Categorize transactions
categorize_transactions(csv_path, categorized_csv_path)

print("✅ Pipeline complete")