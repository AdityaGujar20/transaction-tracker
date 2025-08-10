import json
import pandas as pd

from langchain.schema import HumanMessage, SystemMessage
from langchain_community.chat_models import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback

import os
import logging
from typing import Dict, List
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchTransactionCategorizer:
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize the batch transaction categorizer
        """
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model_name,
            temperature=0.1,
            max_tokens=4000  # Increased for batch processing
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

    def csv_to_json(self, csv_path: str) -> List[Dict]:
        """
        Convert CSV file to JSON format suitable for LLM processing
        """
        try:
            df = pd.read_csv(csv_path)
            
            # Select relevant columns for categorization
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
            logger.error(f"Error converting CSV to JSON: {str(e)}")
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

    def batch_categorize_all_transactions(self, transactions: List[Dict], batch_size: int = 50) -> Dict[int, str]:
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

    def json_results_to_csv(self, original_csv_path: str, categorization_results: Dict[int, str], output_csv_path: str):
        """
        Apply categorization results to original CSV and save
        """
        try:
            # Read original CSV
            df = pd.read_csv(original_csv_path)
            
            # Add category column
            categories = []
            for index in range(len(df)):
                category = categorization_results.get(index, "Miscellaneous")
                categories.append(category)
            
            df['Category'] = categories
            
            # Save to new CSV
            df.to_csv(output_csv_path, index=False)
            logger.info(f"Categorized CSV saved to: {output_csv_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error saving results to CSV: {str(e)}")
            raise

def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)

def main():
    """
    Main function to process transactions using JSON batch approach
    """
    OPENAI_API_KEY = api_key
    
    # Configuration
    project_root = get_project_root()
    csv_input_path = os.path.join(project_root, "data", "processed", "bank_transactions.csv")
    csv_output_path = os.path.join(project_root, "data", "processed", "categorized_bank_transactions_batch.csv")
    json_temp_path = os.path.join(project_root, "data", "processed", "temp_transactions.json")
    
    print("=== BATCH TRANSACTION CATEGORIZATION ===")
    print(f"Input: {csv_input_path}")
    print(f"Output: {csv_output_path}")
    
    # Initialize categorizer with GPT-3.5-turbo for testing
    categorizer = BatchTransactionCategorizer(OPENAI_API_KEY, model_name="gpt-3.5-turbo")
    
    try:
        # Step 1: Convert CSV to JSON
        print("\n1. Converting CSV to JSON...")
        transactions_json = categorizer.csv_to_json(csv_input_path)
        
        # Optionally save JSON for debugging
        with open(json_temp_path, 'w') as f:
            json.dump(transactions_json, f, indent=2)
        print(f"   JSON saved to: {json_temp_path}")
        
        # Step 2: Batch categorize using JSON
        print("\n2. Categorizing transactions...")
        categorization_results = categorizer.batch_categorize_all_transactions(
            transactions_json, 
            batch_size=20  # Smaller batch size for GPT-3.5-turbo
        )
        
        # Step 3: Convert results back to CSV
        print("\n3. Converting results back to CSV...")
        df_categorized = categorizer.json_results_to_csv(
            csv_input_path, 
            categorization_results, 
            csv_output_path
        )
        
        # Display summary
        print("\n=== CATEGORIZATION SUMMARY ===")
        category_counts = df_categorized['Category'].value_counts()
        total_transactions = len(df_categorized)
        
        for category, count in category_counts.items():
            percentage = (count / total_transactions) * 100
            print(f"{category:25}: {count:4d} transactions ({percentage:5.1f}%)")
        
        print(f"\nTotal transactions processed: {total_transactions}")
        
        # Clean up temp file
        if os.path.exists(json_temp_path):
            os.remove(json_temp_path)
            
        print(f"\n✅ Processing complete! Results saved to: {csv_output_path}")
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()