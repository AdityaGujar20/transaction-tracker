import pandas as pd

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialAnalyzer:
    def __init__(self, json_file_path: str = "../data/processed/categorized_transactions.json"):
        """Initialize with path to categorized transactions JSON file"""
        self.json_file_path = Path(json_file_path)
        self.transactions = []
        self.df = None
        self.load_transactions()
    
    def load_transactions(self):
        """Load categorized transactions from JSON file"""
        try:
            if not self.json_file_path.exists():
                logger.error(f"Transactions file not found: {self.json_file_path}")
                raise FileNotFoundError(f"No categorized transactions found at {self.json_file_path}")
            
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.transactions = json.load(f)
            
            if not self.transactions:
                logger.warning("No transactions found in the file")
                return
            
            # Convert to DataFrame for easier analysis
            self.df = pd.DataFrame(self.transactions)
            
            # Convert date column if it exists
            if 'Date' in self.df.columns:
                self.df['Date'] = pd.to_datetime(self.df['Date'])
            
            # Fill NaN values with 0 for numeric columns
            numeric_cols = ['Withdrawal(Dr)', 'Deposit(Cr)', 'Balance']
            for col in numeric_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
            
            logger.info(f"Loaded {len(self.transactions)} transactions successfully")
            
        except Exception as e:
            logger.error(f"Error loading transactions: {str(e)}")
            raise e
    
    def get_total_spending(self) -> float:
        """Calculate total spending (sum of all withdrawals)"""
        if self.df is None or self.df.empty:
            return 0.0
        
        total = self.df['Withdrawal(Dr)'].sum()
        return float(total)
    
    def get_total_income(self) -> float:
        """Calculate total income (sum of all deposits)"""
        if self.df is None or self.df.empty:
            return 0.0
        
        total = self.df['Deposit(Cr)'].sum()
        return float(total)
    
    def get_highest_single_expense(self) -> Dict:
        """Find the highest single expense transaction"""
        if self.df is None or self.df.empty:
            return {"amount": 0, "narration": "No transactions found", "date": None}
        
        # Filter only withdrawal transactions
        expenses = self.df[self.df['Withdrawal(Dr)'] > 0]
        
        if expenses.empty:
            return {"amount": 0, "narration": "No expense transactions found", "date": None}
        
        max_expense_row = expenses.loc[expenses['Withdrawal(Dr)'].idxmax()]
        
        return {
            "amount": float(max_expense_row['Withdrawal(Dr)']),
            "narration": str(max_expense_row['Narration']),
            "date": str(max_expense_row['Date']) if 'Date' in max_expense_row else None,
            "category": str(max_expense_row.get('Category', 'Unknown'))
        }
    
    def get_category_wise_spending(self) -> Dict[str, float]:
        """Calculate spending for each category"""
        if self.df is None or self.df.empty:
            return {}
        
        # Filter only withdrawal transactions and group by category
        expenses = self.df[self.df['Withdrawal(Dr)'] > 0]
        
        if expenses.empty:
            return {}
        
        category_spending = expenses.groupby('Category')['Withdrawal(Dr)'].sum()
        
        # Convert to regular dict with float values
        return {category: float(amount) for category, amount in category_spending.items()}
    
    def get_highest_spending_category(self) -> Dict:
        """Find which category has the highest total spending"""
        category_spending = self.get_category_wise_spending()
        
        if not category_spending:
            return {"category": "No categories found", "amount": 0}
        
        max_category = max(category_spending.items(), key=lambda x: x[1])
        
        return {
            "category": max_category[0],
            "amount": max_category[1]
        }
    
    def get_net_balance_change(self) -> float:
        """Calculate net change (income - spending)"""
        return self.get_total_income() - self.get_total_spending()
    
    def get_transaction_count_by_type(self) -> Dict:
        """Get count of income vs expense transactions"""
        if self.df is None or self.df.empty:
            return {"income_transactions": 0, "expense_transactions": 0, "total": 0}
        
        income_count = len(self.df[self.df['Deposit(Cr)'] > 0])
        expense_count = len(self.df[self.df['Withdrawal(Dr)'] > 0])
        
        return {
            "income_transactions": income_count,
            "expense_transactions": expense_count,
            "total": len(self.df)
        }
    
    def get_monthly_spending_summary(self) -> Dict:
        """Get spending summary by month (if date info available)"""
        if self.df is None or self.df.empty or 'Date' not in self.df.columns:
            return {}
        
        # Group by month-year
        self.df['Month_Year'] = self.df['Date'].dt.to_period('M')
        monthly_expenses = self.df[self.df['Withdrawal(Dr)'] > 0].groupby('Month_Year')['Withdrawal(Dr)'].sum()
        
        return {str(month): float(amount) for month, amount in monthly_expenses.items()}

def generate_financial_qa_json(json_file_path: str = "../data/processed/categorized_transactions.json", 
                               output_path: str = "../data/processed/financial_analysis_qa.json") -> Dict:
    """
    Generate financial analysis in Question-Answer format and save to JSON
    """
    try:
        print("\n" + "="*60)
        print("💰 GENERATING FINANCIAL Q&A ANALYSIS")
        print("="*60)
        
        analyzer = FinancialAnalyzer(json_file_path)
        
        # Get raw data for calculations
        total_spending = analyzer.get_total_spending()
        total_income = analyzer.get_total_income()
        net_balance = analyzer.get_net_balance_change()
        highest_expense = analyzer.get_highest_single_expense()
        highest_category = analyzer.get_highest_spending_category()
        category_spending = analyzer.get_category_wise_spending()
        transaction_counts = analyzer.get_transaction_count_by_type()
        monthly_summary = analyzer.get_monthly_spending_summary()
        
        # Format category spending for display
        category_breakdown = ""
        for category, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True):
            category_breakdown += f"• {category}: ₹{amount:,.2f}\n"
        category_breakdown = category_breakdown.strip()
        
        # Format monthly summary for display
        monthly_breakdown = ""
        if monthly_summary:
            for month, amount in monthly_summary.items():
                monthly_breakdown += f"• {month}: ₹{amount:,.2f}\n"
            monthly_breakdown = monthly_breakdown.strip()
        else:
            monthly_breakdown = "Monthly data not available"
        
        # Create Question-Answer pairs
        qa_data = {
            "financial_analysis": {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_transactions_analyzed": transaction_counts.get('total', 0),
                    "source_file": str(json_file_path)
                },
                "questions_and_answers": [
                    {
                        "question": "What is my total spending?",
                        "answer": f"Your total spending is ₹{total_spending:,.2f}",
                        "raw_data": total_spending
                    },
                    {
                        "question": "What is my total income?",
                        "answer": f"Your total income is ₹{total_income:,.2f}",
                        "raw_data": total_income
                    },
                    {
                        "question": "What is my net balance change?",
                        "answer": f"Your net balance change is ₹{net_balance:,.2f} ({'profit' if net_balance >= 0 else 'loss'})",
                        "raw_data": net_balance
                    },
                    {
                        "question": "What is my highest single expense?",
                        "answer": f"Your highest single expense is ₹{highest_expense['amount']:,.2f} for '{highest_expense['narration'][:50]}...' in the {highest_expense['category']} category",
                        "raw_data": highest_expense
                    },
                    {
                        "question": "Which category do I spend the most on?",
                        "answer": f"You spend the most on {highest_category['category']} with a total of ₹{highest_category['amount']:,.2f}",
                        "raw_data": highest_category
                    },
                    {
                        "question": "How much did I spend on each category?",
                        "answer": f"Here's your spending by category:\n{category_breakdown}",
                        "raw_data": category_spending
                    },
                    {
                        "question": "How many transactions do I have?",
                        "answer": f"You have {transaction_counts['total']} total transactions: {transaction_counts['income_transactions']} income transactions and {transaction_counts['expense_transactions']} expense transactions",
                        "raw_data": transaction_counts
                    },
                    {
                        "question": "What is my monthly spending breakdown?",
                        "answer": f"Your monthly spending breakdown:\n{monthly_breakdown}",
                        "raw_data": monthly_summary
                    }
                ]
            }
        }
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(qa_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Financial Q&A analysis saved to: {output_file}")
        print(f"📊 Generated {len(qa_data['financial_analysis']['questions_and_answers'])} Q&A pairs")
        
        # Print summary to console
        print("\n" + "="*40)
        print("📋 SUMMARY OF QUESTIONS & ANSWERS")
        print("="*40)
        for qa in qa_data['financial_analysis']['questions_and_answers']:
            print(f"\n❓ {qa['question']}")
            print(f"💬 {qa['answer']}")
        
        print("="*60)
        return qa_data
        
    except Exception as e:
        logger.error(f"Error in financial Q&A generation: {str(e)}")
        print(f"❌ Financial Q&A generation failed: {str(e)}")
        return {}

# Updated specific question answering functions that also save to JSON
def save_single_qa_to_json(question: str, answer: str, raw_data: any, 
                          output_path: str = "../data/processed/single_qa.json"):
    """Save a single Q&A to JSON file"""
    qa_data = {
        "question": question,
        "answer": answer,
        "raw_data": raw_data,
        "generated_at": datetime.now().isoformat()
    }
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(qa_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Q&A saved to: {output_file}")

def ask_total_spending(json_file_path: str = "../data/processed/categorized_transactions.json", 
                      save_json: bool = False) -> str:
    """Answer: What is my total spending?"""
    try:
        analyzer = FinancialAnalyzer(json_file_path)
        total = analyzer.get_total_spending()
        answer = f"Your total spending is ₹{total:,.2f}"
        
        if save_json:
            save_single_qa_to_json("What is my total spending?", answer, total)
        
        return answer
    except Exception as e:
        return f"Sorry, I couldn't calculate your total spending. Error: {str(e)}"

def ask_highest_spending_category(json_file_path: str = "../data/processed/categorized_transactions.json",
                                 save_json: bool = False) -> str:
    """Answer: Which category do I spend the most on?"""
    try:
        analyzer = FinancialAnalyzer(json_file_path)
        result = analyzer.get_highest_spending_category()
        answer = f"You spend the most on {result['category']} with a total of ₹{result['amount']:,.2f}"
        
        if save_json:
            save_single_qa_to_json("Which category do I spend the most on?", answer, result)
        
        return answer
    except Exception as e:
        return f"Sorry, I couldn't determine your highest spending category. Error: {str(e)}"

def ask_total_income(json_file_path: str = "../data/processed/categorized_transactions.json",
                    save_json: bool = False) -> str:
    """Answer: What is my total income?"""
    try:
        analyzer = FinancialAnalyzer(json_file_path)
        total = analyzer.get_total_income()
        answer = f"Your total income is ₹{total:,.2f}"
        
        if save_json:
            save_single_qa_to_json("What is my total income?", answer, total)
        
        return answer
    except Exception as e:
        return f"Sorry, I couldn't calculate your total income. Error: {str(e)}"

def ask_highest_single_expense(json_file_path: str = "../data/processed/categorized_transactions.json",
                              save_json: bool = False) -> str:
    """Answer: What is my highest single expense?"""
    try:
        analyzer = FinancialAnalyzer(json_file_path)
        result = analyzer.get_highest_single_expense()
        answer = f"Your highest single expense is ₹{result['amount']:,.2f} for {result['narration'][:30]}... in {result['category']} category"
        
        if save_json:
            save_single_qa_to_json("What is my highest single expense?", answer, result)
        
        return answer
    except Exception as e:
        return f"Sorry, I couldn't find your highest single expense. Error: {str(e)}"

def ask_category_spending(json_file_path: str = "../data/processed/categorized_transactions.json",
                         save_json: bool = False) -> str:
    """Answer: How much did I spend on each category?"""
    try:
        analyzer = FinancialAnalyzer(json_file_path)
        category_spending = analyzer.get_category_wise_spending()
        
        if not category_spending:
            return "No spending data found."
        
        response = "Here's your spending by category:\n"
        for category, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True):
            response += f"• {category}: ₹{amount:,.2f}\n"
        
        if save_json:
            save_single_qa_to_json("How much did I spend on each category?", response, category_spending)
        
        return response
    except Exception as e:
        return f"Sorry, I couldn't calculate category-wise spending. Error: {str(e)}"

# Test function updated to use JSON output
def test_financial_analyzer_with_json():
    """Test function to check if analysis is working and generate JSON output"""
    try:
        print("Testing Financial Analyzer with JSON Output...")
        
        # Generate complete Q&A JSON
        qa_data = generate_financial_qa_json()
        
        if qa_data:
            print("\n🧪 Testing Individual Q&A Functions (with JSON save):")
            print("Q: What is my total spending?")
            print("A:", ask_total_spending(save_json=True))
            
            print("\nQ: Which category do I spend the most on?")
            print("A:", ask_highest_spending_category(save_json=True))
            
            print("\nQ: What is my total income?") 
            print("A:", ask_total_income(save_json=True))
            
            print("\nQ: What is my highest single expense?")
            print("A:", ask_highest_single_expense(save_json=True))
            
            print("\nQ: How much did I spend on each category?")
            print("A:", ask_category_spending(save_json=True))
            
            print("\n✅ All tests completed successfully!")
            print("📁 Check ../data/processed/ folder for JSON output files")
            
        else:
            print("❌ Test failed - no data available")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    # Run test with JSON output when file is executed directly
    test_financial_analyzer_with_json()