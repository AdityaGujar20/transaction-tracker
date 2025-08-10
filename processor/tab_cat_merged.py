import pdfplumber
import re
import pandas as pd
import json
from datetime import datetime
from decimal import Decimal
import os
import logging
from typing import Dict, List

from langchain.schema import HumanMessage, SystemMessage
from langchain_community.chat_models import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BankStatementProcessor:
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize the bank statement processor with PDF extraction and LLM categorization
        """
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model_name,
            temperature=0.1,
            max_tokens=4000
        )
        
        # Define categories
        self.categories = [
            "Food & Dining",
            "Transportation", 
            "Shopping",
            "Healthcare",
            "Entertainment",
            "Utilities & Bills",
            "Financial Services",
            "Personal Care",
            "Education",
            "Transfer/Refund",
            "Miscellaneous"
        ]

    def extract_bank_statement_table(self, pdf_path):
        """
        Extract transaction table from bank statement PDF
        """
        transactions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Split text into lines
                    lines = text.split('\n')
                    
                    # Process each line to find transaction entries
                    for i, line in enumerate(lines):
                        # Look for date pattern (DD-MM-YYYY)
                        date_pattern = r'(\d{2}-\d{2}-\d{4})'
                        date_match = re.search(date_pattern, line)
                        
                        if date_match:
                            date_str = date_match.group(1)
                            
                            # Skip header lines
                            if 'Date' in line or 'Narration' in line:
                                continue
                                
                            # Extract transaction details
                            transaction = self.extract_transaction_details(line, lines[i:i+3])
                            if transaction:
                                transactions.append(transaction)
        
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        return df

    def extract_transaction_details(self, line, context_lines):
        """
        Extract individual transaction details from a line
        """
        try:
            # Date pattern
            date_pattern = r'(\d{2}-\d{2}-\d{4})'
            date_match = re.search(date_pattern, line)
            if not date_match:
                return None
                
            date_str = date_match.group(1)
            
            # Amount patterns - look for amounts with (Dr) or (Cr)
            amount_pattern = r'([\d,]+\.?\d*)\s*\((Dr|Cr)\)'
            amounts = re.findall(amount_pattern, line)
            
            if len(amounts) < 2:  # Need at least withdrawal/deposit and balance
                return None
                
            # Extract narration (everything between date and first amount)
            narration_start = date_match.end()
            first_amount_pos = line.find(amounts[0][0])
            narration = line[narration_start:first_amount_pos].strip()
            
            # Extract reference number (if present)
            ref_pattern = r'([A-Z0-9\-]+)\s*(?=[\d,]+\.?\d*\s*\()'
            ref_match = re.search(ref_pattern, narration)
            ref_no = ref_match.group(1) if ref_match else ""
            
            # Clean narration (remove reference number)
            if ref_no:
                narration = narration.replace(ref_no, "").strip()
            
            # Parse amounts
            withdrawal_amount = 0.0
            deposit_amount = 0.0
            balance = 0.0
            
            # First amount is either withdrawal or deposit
            first_amount = float(amounts[0][0].replace(',', ''))
            if amounts[0][1] == 'Dr':
                withdrawal_amount = first_amount
            else:
                deposit_amount = first_amount
                
            # Last amount is balance
            balance = float(amounts[-1][0].replace(',', ''))
            
            return {
                'Date': date_str,
                'Narration': narration.strip(),
                'Chq/Ref No': ref_no,
                'Withdrawal(Dr)': withdrawal_amount if withdrawal_amount > 0 else None,
                'Deposit(Cr)': deposit_amount if deposit_amount > 0 else None,
                'Balance': balance
            }
            
        except Exception as e:
            print(f"Error processing line: {line[:50]}... Error: {str(e)}")
            return None

    def extract_transactions_regex(self, pdf_path):
        """
        Alternative method using comprehensive regex pattern
        """
        transactions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        # Comprehensive regex pattern for transaction lines
        transaction_pattern = r'''
            (\d{2}-\d{2}-\d{4})\s+          # Date
            (.+?)\s+                         # Narration (non-greedy)
            ([A-Z0-9\-/]*)\s*               # Reference number (optional)
            ([\d,]+\.?\d*)\s*\((Dr|Cr)\)\s+ # Withdrawal/Deposit amount
            ([\d,]+\.?\d*)\s*\(Cr\)         # Balance
        '''
        
        matches = re.findall(transaction_pattern, full_text, re.VERBOSE | re.MULTILINE)
        
        for match in matches:
            date_str, narration, ref_no, amount, dr_cr, balance = match
            
            withdrawal = float(amount.replace(',', '')) if dr_cr == 'Dr' else 0
            deposit = float(amount.replace(',', '')) if dr_cr == 'Cr' else 0
            
            transactions.append({
                'Date': date_str,
                'Narration': narration.strip(),
                'Chq/Ref No': ref_no.strip(),
                'Withdrawal(Dr)': withdrawal if withdrawal > 0 else None,
                'Deposit(Cr)': deposit if deposit > 0 else None,
                'Balance': float(balance.replace(',', ''))
            })
        
        return pd.DataFrame(transactions)

    def clean_and_format_data(self, df):
        """
        Clean and format the extracted data
        """
        if df.empty:
            return df
            
        # Convert date strings to datetime
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Fill NaN values appropriately
        df['Withdrawal(Dr)'] = df['Withdrawal(Dr)'].fillna(0)
        df['Deposit(Cr)'] = df['Deposit(Cr)'].fillna(0)
        
        return df

    def df_to_json_for_categorization(self, df: pd.DataFrame) -> List[Dict]:
        """
        Convert DataFrame to JSON format suitable for LLM processing
        This mirrors the original csv_to_json method from the second file
        """
        try:
            categorization_data = []
            
            for index, row in df.iterrows():
                transaction = {
                    "id": index,
                    "date": str(row.get('Date', '')),
                    "narration": str(row.get('Narration', '')),
                    "amount": float(row.get('Withdrawal(Dr)', 0)) if pd.notna(row.get('Withdrawal(Dr)')) else float(row.get('Deposit(Cr)', 0)),
                    "type": "debit" if pd.notna(row.get('Withdrawal(Dr)')) and row.get('Withdrawal(Dr)') > 0 else "credit"
                }
                categorization_data.append(transaction)
            
            logger.info(f"Converted {len(categorization_data)} transactions to JSON format")
            return categorization_data
            
        except Exception as e:
            logger.error(f"Error converting DataFrame to JSON: {str(e)}")
            raise

    def create_batch_categorization_prompt(self, transactions: List[Dict]) -> List:
        """
        Create a comprehensive prompt for batch categorization
        """
        categories_text = ", ".join(self.categories)
        
        system_message = f"""You are a financial transaction categorizer. Your task is to categorize a batch of bank transactions into one of these categories:

{categories_text}

Rules:
1. Return ONLY a valid JSON array with the same number of items as input
2. Each item should have "id" and "category" fields
3. Be consistent with similar transactions
4. Consider Indian business names and UPI transaction patterns
5. Use context clues from merchant names and descriptions
6. For unclear transactions, use "Miscellaneous"

Output format:
[
  {{"id": 0, "category": "Food & Dining"}},
  {{"id": 1, "category": "Transportation"}},
  ...
]

Examples:
- "UPI/Juice Bar/..." → Food & Dining
- "UPI/BOMBLE SHIVAM V/cab" → Transportation
- "PURCHASE OF MUTUALFUND" → Financial Services
- "UPI/Primo Salon/..." → Personal Care
- "UPI/BEYOND HEALTH C/..." → Healthcare
- "NACH-MUT-DR-GROWW PAY" → Financial Services
- "UPI/AMAZON" → Shopping
- "PVR INOX" → Entertainment
"""

        # Prepare transaction data for the prompt
        transaction_text = "Transactions to categorize:\n"
        for tx in transactions:
            transaction_text += f"ID {tx['id']}: {tx['narration']} (₹{tx['amount']} - {tx['type']})\n"

        human_message = transaction_text

        return [
            SystemMessage(content=system_message),
            HumanMessage(content=human_message)
        ]

    def batch_categorize_all_transactions(self, transactions: List[Dict], batch_size: int = 20) -> Dict[int, str]:
        """
        Process all transactions in batches and return categorization results
        """
        all_results = {}
        total_batches = (len(transactions) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(transactions)} transactions in {total_batches} batches")
        
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} transactions)")
            
            try:
                with get_openai_callback() as cb:
                    messages = self.create_batch_categorization_prompt(batch)
                    response = self.llm(messages)
                    
                    # Parse JSON response
                    response_text = response.content.strip()
                    
                    # Clean response if it has markdown formatting
                    if response_text.startswith("```json"):
                        response_text = response_text.replace("```json", "").replace("```", "").strip()
                    elif response_text.startswith("```"):
                        response_text = response_text.replace("```", "").strip()
                    
                    batch_results = json.loads(response_text)
                    
                    # Validate results
                    if len(batch_results) != len(batch):
                        logger.warning(f"Batch {batch_num}: Expected {len(batch)} results, got {len(batch_results)}")
                    
                    # Store results
                    for result in batch_results:
                        if isinstance(result, dict) and 'id' in result and 'category' in result:
                            all_results[result['id']] = result['category']
                        else:
                            logger.warning(f"Invalid result format in batch {batch_num}: {result}")
                    
                    logger.info(f"Batch {batch_num} completed. Tokens: {cb.total_tokens}, Cost: ${cb.total_cost:.4f}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in batch {batch_num}: {str(e)}")
                logger.error(f"Response was: {response.content[:500]}...")
                
                # Fallback: assign Miscellaneous to all transactions in this batch
                for tx in batch:
                    all_results[tx['id']] = "Miscellaneous"
                    
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {str(e)}")
                
                # Fallback: assign Miscellaneous to all transactions in this batch
                for tx in batch:
                    all_results[tx['id']] = "Miscellaneous"
        
        return all_results

    def add_categories_to_json(self, transactions: List[Dict], categorization_results: Dict[int, str]) -> List[Dict]:
        """
        Add category information to the JSON transactions and restore full transaction data
        """
        for transaction in transactions:
            transaction_id = transaction['id']
            category = categorization_results.get(transaction_id, "Miscellaneous")
            transaction['category'] = category
        
        return transactions

    def process_pdf_to_categorized_json(self, pdf_path: str, output_json_path: str):
        """
        Main function to process PDF bank statement to categorized JSON
        """
        print("=== BANK STATEMENT PROCESSING ===")
        print(f"Input PDF: {pdf_path}")
        print(f"Output JSON: {output_json_path}")
        
        # Step 1: Extract transactions from PDF
        print("\n1. Extracting transactions from PDF...")
        try:
            df = self.extract_bank_statement_table(pdf_path)
            df = self.clean_and_format_data(df)
            
            if df.empty:
                print("First method failed, trying alternative approach...")
                df = self.extract_transactions_regex(pdf_path)
                df = self.clean_and_format_data(df)
                
        except Exception as e:
            print(f"Error: {e}")
            print("Trying alternative approach...")
            df = self.extract_transactions_regex(pdf_path)
            df = self.clean_and_format_data(df)
        
        if df.empty:
            raise ValueError("No transactions found in the PDF. Please check the PDF format.")
        
        print(f"   Successfully extracted {len(df)} transactions")
        
        # Step 2: Convert DataFrame to JSON format for LLM
        print("\n2. Converting to JSON format...")
        transactions_json = self.df_to_json_for_categorization(df)
        
        # Debug: Print a few sample transactions
        print(f"   Sample transactions for categorization:")
        for i, tx in enumerate(transactions_json[:3]):
            print(f"   {i}: {tx['narration'][:50]}... (₹{tx['amount']} - {tx['type']})")
        
        
        # Step 3: Categorize transactions using LLM
        print("\n3. Categorizing transactions using LLM...")
        categorization_results = self.batch_categorize_all_transactions(transactions_json, batch_size=20)
        
        # Step 4: Add categories to JSON
        print("\n4. Adding categories to final JSON...")
        final_json = self.add_categories_to_json(transactions_json, categorization_results)
        
        # Step 5: Save final JSON
        print("\n5. Saving final JSON...")
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"   Final JSON saved to: {output_json_path}")
        
        # Display summary
        print("\n=== PROCESSING SUMMARY ===")
        categories = {}
        for transaction in final_json:
            category = transaction.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        total_transactions = len(final_json)
        for category, count in sorted(categories.items()):
            percentage = (count / total_transactions) * 100
            print(f"{category:25}: {count:4d} transactions ({percentage:5.1f}%)")
        
        print(f"\nTotal transactions processed: {total_transactions}")
        print(f"✅ Processing complete!")
        
        return final_json

def main():
    """
    Main function to process bank statement PDF to categorized JSON
    """
    # Configuration
    OPENAI_API_KEY = api_key
    
    if not OPENAI_API_KEY:
        raise ValueError("Please set OPENAI_API_KEY in your environment variables")
    
    # File paths - update these as needed
    pdf_path = "../data/raw/kotak-bankstatement.pdf"  # Input PDF path
    output_json_path = "../data/processed/categorized_transactions.json"  # Output JSON path
    
    # Initialize processor
    processor = BankStatementProcessor(OPENAI_API_KEY, model_name="gpt-3.5-turbo")
    
    try:
        # Process PDF to categorized JSON
        final_json = processor.process_pdf_to_categorized_json(pdf_path, output_json_path)
        
        print(f"\n🎉 Success! Categorized transactions saved to: {output_json_path}")
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()