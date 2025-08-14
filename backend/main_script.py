import json

from core.table_extractor import extract_pdf_to_json
from core.categorizer import categorize_transactions_json

def main():
    """Main pipeline function"""
    # pdf_path = "data/raw/kotak-bankstatement-1y-1-4.pdf"
    pdf_path = "data/raw"
    processed_dir = "data/processed"
    
    print("🚀 Starting Bank Statement Processing Pipeline")
    print("=" * 60)
    
    try:
        # Step 1: Extract transactions from PDF to JSON
        print("Step 1: Extracting transactions from PDF...")
        transactions_json = extract_pdf_to_json(pdf_path)
        
        if not transactions_json:
            print("❌ No transactions found in PDF")
            return
        
        print(f"✅ Extracted {len(transactions_json)} transactions")
        
        # Step 2: Categorize transactions and save to processed folder
        print("\nStep 2: Categorizing transactions...")
        categorized_transactions = categorize_transactions_json(transactions_json, processed_dir)
        
        print(f"✅ Categorized {len(categorized_transactions)} transactions")
        
        # Display summary
        print("\n" + "="*60)
        print("📊 PIPELINE SUMMARY")
        print("="*60)
        
        # Count categories
        category_counts = {}
        for tx in categorized_transactions:
            category = tx.get('Category', 'Unknown')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        print(f"📄 Total Transactions: {len(categorized_transactions)}")
        print(f"📁 Output File: {processed_dir}/categorized_transactions.json")
        print("\n📈 Category Breakdown:")
        
        for category, count in sorted(category_counts.items()):
            percentage = (count / len(categorized_transactions)) * 100
            print(f"  • {category}: {count} ({percentage:.1f}%)")
        
        print("\n✅ Pipeline completed successfully!")
        print("="*60)
        
        return categorized_transactions
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {str(e)}")
        print(f"Error details: {type(e).__name__}: {e}")
        raise e

if __name__ == "__main__":
    main()