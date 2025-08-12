import json
import pandas as pd
import os
import logging
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
import openai
from pathlib import Path

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchTransactionCategorizer:
    def __init__(self, openai_api_key: str):
        """Initialize OpenAI client - compatible with both old and new versions"""
        # Set API key
        openai.api_key = openai_api_key
        
        # Check OpenAI version and initialize accordingly
        try:
            # For OpenAI v1.0+ (new version)
            self.client = openai.OpenAI(api_key=openai_api_key)
            self.use_new_client = True
            logger.info("Using OpenAI v1.0+ client")
        except AttributeError:
            # For OpenAI v0.x (old version)
            self.client = None
            self.use_new_client = False
            logger.info("Using OpenAI v0.x client")
        
        self.categories = [
            "Food & Dining", "Transportation", "Shopping", "Healthcare",
            "Entertainment", "Utilities & Bills", "Financial Services",
            "Personal Care", "Education", "Transfer/Refund", "Miscellaneous"
        ]

    def json_to_categorization_format(self, transactions_json: List[Dict]) -> List[Dict]:
        """Convert transactions JSON to categorization format"""
        categorization_data = []
        for index, transaction in enumerate(transactions_json):
            tx = {
                "id": index,
                "date": str(transaction.get('Date', '')),
                "narration": str(transaction.get('Narration', '')),
                "amount": float(transaction.get('Withdrawal(Dr)', 0)) if transaction.get('Withdrawal(Dr)') else float(transaction.get('Deposit(Cr)', 0)),
                "type": "debit" if transaction.get('Withdrawal(Dr)') and transaction.get('Withdrawal(Dr)') > 0 else "credit"
            }
            categorization_data.append(tx)
        logger.info(f"Converted {len(categorization_data)} transactions to categorization format")
        return categorization_data

    def create_categorization_prompt(self, transactions: List[Dict]) -> str:
        """Create prompt for OpenAI API"""
        categories_text = ", ".join(self.categories)
        
        prompt = f"""You are a financial transaction categorizer. Categorize these bank transactions based on their narration.

Available Categories: {categories_text}

Categorization Rules:
1. Food & Dining: Restaurants, food delivery, groceries, cafes, supermarkets, food vendors
2. Transportation: Uber, Ola, petrol, metro, bus, taxi, parking, fuel
3. Shopping: Online shopping, retail stores, clothing, electronics, Amazon, Flipkart
4. Healthcare: Hospitals, clinics, pharmacies, medical stores, health insurance, chemists
5. Entertainment: Movies, games, streaming services, sports, recreation
6. Utilities & Bills: Electricity, water, gas, internet, phone bills, rent, recharge
7. Financial Services: Bank charges, loan payments, insurance, investments, mutual funds, SIP
8. Personal Care: Salon, spa, cosmetics, personal hygiene products
9. Education: Schools, courses, books, training, tuition
10. Transfer/Refund: Money transfers to/from individuals, refunds, reversals, person names
11. Miscellaneous: Everything else that doesn't fit the above categories

Key Guidelines:
- For UPI transactions with person names (like "ADITYA ANIL", "KALPANA DEBNAT"), use "Transfer/Refund"
- For business names, categorize based on the business type
- Look for keywords in merchant names
- When uncertain, use "Transfer/Refund" for person-to-person transfers, otherwise "Miscellaneous"

Transactions to categorize:
"""
        
        for tx in transactions:
            prompt += f"ID {tx['id']}: {tx['narration']} (₹{tx['amount']} - {tx['type']})\n"
        
        prompt += "\nReturn ONLY a JSON array with format: [{\"id\": 0, \"category\": \"Category Name\"}, ...]"
        
        return prompt

    def call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API - compatible with both old and new versions"""
        try:
            if self.use_new_client:
                # New client (v1.0+)
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            else:
                # Old client (v0.x)
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise e

    def batch_categorize_all_transactions(self, transactions: List[Dict], batch_size: int = 10) -> Dict[int, str]:
        """Categorize transactions using OpenAI API calls"""
        all_results = {}
        total_batches = (len(transactions) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(transactions)} transactions in {total_batches} batches of {batch_size}")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(transactions))
            batch = transactions[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} transactions)")
            
            try:
                # Create prompt
                prompt = self.create_categorization_prompt(batch)
                
                # Call OpenAI API
                response_text = self.call_openai_api(prompt)
                logger.info(f"Raw API response: {response_text[:200]}...")
                
                # Clean up the response
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                response_text = response_text.strip()
                
                # Parse JSON response
                try:
                    batch_results = json.loads(response_text)
                    
                    if isinstance(batch_results, list):
                        success_count = 0
                        for result in batch_results:
                            if isinstance(result, dict) and 'id' in result and 'category' in result:
                                category = result['category']
                                # Validate category
                                if category in self.categories:
                                    all_results[result['id']] = category
                                    success_count += 1
                                else:
                                    logger.warning(f"Invalid category '{category}' for transaction {result['id']}")
                                    all_results[result['id']] = "Miscellaneous"
                                    success_count += 1
                        
                        logger.info(f"Batch {batch_num + 1} completed: {success_count}/{len(batch)} transactions categorized")
                        
                    else:
                        logger.error(f"Response is not a list: {type(batch_results)}")
                        raise ValueError("Response is not a list")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {e}")
                    logger.error(f"Response text: {response_text}")
                    raise e
                    
            except Exception as e:
                logger.error(f"Error processing batch {batch_num + 1}: {str(e)}")
                
                # Enhanced fallback categorization
                for tx in batch:
                    if tx['id'] not in all_results:
                        category = self.enhanced_categorize(tx['narration'])
                        all_results[tx['id']] = category
                        logger.info(f"Fallback categorization for {tx['id']}: {category}")
        
        logger.info(f"Categorization complete. Total results: {len(all_results)}")
        return all_results

    def enhanced_categorize(self, narration: str) -> str:
        """Enhanced rule-based categorization with better pattern matching"""
        narration_lower = narration.lower()
        
        # Enhanced keyword mappings with more patterns
        keyword_map = {
            "Food & Dining": [
                "super", "restaurant", "food", "zomato", "swiggy", "cafe", "hotel", 
                "mess", "canteen", "dhaba", "bakery", "pizza", "burger", "grocery",
                "mart", "store", "fresh", "fruits", "vegetables", "milk", "bread", "mingos"
            ],
            "Healthcare": [
                "chemist", "pharmacy", "medical", "hospital", "clinic", "health", 
                "doctor", "medicine", "pharma", "apollo", "care", "diagnostics",
                "pathology", "lab", "dental", "eye", "skin"
            ],
            "Transportation": [
                "uber", "ola", "petrol", "fuel", "metro", "bus", "taxi", "auto",
                "rickshaw", "transport", "travel", "booking", "irctc", "railway",
                "airlines", "flight", "cab", "bike", "scooter"
            ],
            "Financial Services": [
                "groww", "mutual", "fund", "bank", "loan", "insurance", "invest",
                "sip", "rd", "fd", "policy", "premium", "emi", "interest", 
                "zerodha", "upstox", "icicidirect", "hdfc", "axis", "kotak"
            ],
            "Transfer/Refund": [
                "transfer", "refund", "neft", "imps", "rtgs", "cashback", 
                "reversal", "credited", "debited"
            ],
            "Utilities & Bills": [
                "electricity", "water", "gas", "bill", "recharge", "mobile",
                "broadband", "internet", "wifi", "jio", "airtel", "vodafone",
                "bsnl", "rent", "maintenance"
            ],
            "Shopping": [
                "amazon", "flipkart", "myntra", "ajio", "shop", "store", "mall",
                "online", "purchase", "buy", "order", "delivery", "ecommerce",
                "fashion", "clothing", "electronics", "mobile", "laptop"
            ],
            "Entertainment": [
                "movie", "netflix", "prime", "hotstar", "spotify", "youtube",
                "game", "gaming", "cinema", "theatre", "show", "concert",
                "music", "subscription", "entertainment"
            ],
            "Personal Care": [
                "salon", "spa", "parlour", "beauty", "cosmetic", "skincare",
                "haircut", "facial", "massage", "grooming"
            ],
            "Education": [
                "school", "college", "university", "course", "training", 
                "education", "tuition", "coaching", "book", "study"
            ]
        }
        
        # Check for person-to-person transfers (common Indian names patterns)
        person_indicators = [
            "upi/", "/upi", "aditya", "kalpana", "pushpa", "nagamma", "fathima",
            "suhara", "clive", "allen", "savitha", "debnat", "mohan", "kumar"
        ]
        
        # If it looks like a person name, categorize as Transfer/Refund
        if any(indicator in narration_lower for indicator in person_indicators):
            # But check if it's actually a business with person's name
            business_keywords = ["super", "store", "shop", "mart", "services", "pvt", "ltd"]
            if not any(biz in narration_lower for biz in business_keywords):
                return "Transfer/Refund"
        
        # Check against keyword mappings
        for category, keywords in keyword_map.items():
            if any(keyword in narration_lower for keyword in keywords):
                return category
        
        # Special patterns
        if "cashback" in narration_lower or "earned" in narration_lower:
            return "Transfer/Refund"
            
        if "int.pd" in narration_lower or "interest" in narration_lower:
            return "Financial Services"
            
        if "adidas" in narration_lower or "nike" in narration_lower:
            return "Shopping"
            
        return "Miscellaneous"

def categorize_transactions_json(transactions_json: List[Dict], processed_dir: str = "data/processed") -> List[Dict]:
    """
    Main function to categorize transactions from JSON data and save to processed folder.
    
    Args:
        transactions_json (List[Dict]): List of transaction dictionaries from table extractor
        processed_dir (str): Directory to save the categorized JSON file
        
    Returns:
        List[Dict]: Categorized transactions as JSON
    """
    try:
        print("\n" + "="*60)
        print("🏷️  TRANSACTION CATEGORIZATION")
        print("="*60)
        
        logger.info(f"Starting transaction categorization for {len(transactions_json)} transactions")
        
        # Check if API key is available
        if not api_key:
            logger.error("OpenAI API key not found. Please check your .env file.")
            raise ValueError("OpenAI API key not found")
        
        # Initialize categorizer
        categorizer = BatchTransactionCategorizer(api_key)
        
        # Convert to categorization format
        categorization_data = categorizer.json_to_categorization_format(transactions_json)
        logger.info(f"Prepared {len(categorization_data)} transactions for categorization")
        
        # Categorize transactions (using smaller batch size for better reliability)
        results = categorizer.batch_categorize_all_transactions(categorization_data, batch_size=8)
        
        # Add categories to original transactions
        categorized_transactions = []
        for i, transaction in enumerate(transactions_json):
            categorized_tx = transaction.copy()
            categorized_tx['Category'] = results.get(i, "Miscellaneous")
            categorized_transactions.append(categorized_tx)
        
        # Save to processed directory
        processed_path = Path(processed_dir)
        processed_path.mkdir(parents=True, exist_ok=True)
        
        output_file = processed_path / "categorized_transactions.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categorized_transactions, f, ensure_ascii=False, indent=2)
        
        # Log category distribution
        category_counts = {}
        for tx in categorized_transactions:
            category = tx['Category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        logger.info("Category distribution:")
        for category, count in category_counts.items():
            logger.info(f"  {category}: {count}")
        
        print(f"✅ Transaction categorization completed successfully!")
        print(f"📁 Categorized data saved to: {output_file}")
        print(f"📊 Total transactions: {len(categorized_transactions)}")
        print("="*60)
        
        logger.info("Transaction categorization completed successfully!")
        return categorized_transactions
        
    except Exception as e:
        logger.error(f"Error in categorize_transactions_json: {str(e)}")
        print(f"❌ Error in transaction categorization: {str(e)}")
        raise e

# Test function (only runs when script is executed directly)
def test_categorization():
    """Test function to check if categorization is working"""
    sample_transactions = [
        {"Date": "2024-01-01", "Narration": "UPI/Premsagar super/409326729134/UPI", "Withdrawal(Dr)": 210, "Deposit(Cr)": 0, "Balance": 5000},
        {"Date": "2024-01-02", "Narration": "UPI/METRO CHEMIST a/410850854877/UPI", "Withdrawal(Dr)": 100, "Deposit(Cr)": 0, "Balance": 4900},
        {"Date": "2024-01-03", "Narration": "NACH-MUT-DR-GROWW PAY SERVICES", "Withdrawal(Dr)": 100, "Deposit(Cr)": 0, "Balance": 4800},
        {"Date": "2024-01-04", "Narration": "UPI/ADITYA ANIL GUJ/409403199750/UPI", "Withdrawal(Dr)": 0, "Deposit(Cr)": 600, "Balance": 5400},
        {"Date": "2024-01-05", "Narration": "UPI/ADIDAS NEXUS KO/102159664527/UPI", "Withdrawal(Dr)": 2500, "Deposit(Cr)": 0, "Balance": 2900}
    ]
    
    results = categorize_transactions_json(sample_transactions, "test_processed")
    print("Test results:")
    for tx in results:
        print(f"  {tx['Narration'][:30]}... -> {tx['Category']}")

if __name__ == "__main__":
    # Only run test when this file is executed directly
    print("Testing transaction categorizer...")
    test_categorization()