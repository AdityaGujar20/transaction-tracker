import json
import os
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
from pathlib import Path
import re
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client with error handling
client = None

def init_openai_client():
    """Initialize OpenAI client with proper error handling"""
    global client
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables")
            return None
        
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        return None

class TransactionChatbot:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
        self.transactions_data = self.load_transactions()
    
    def load_transactions(self):
        """Load transactions from JSON file"""
        try:
            if os.path.exists(self.json_file_path):
                with open(self.json_file_path, 'r') as file:
                    return json.load(file)
            return []
        except Exception as e:
            print(f"Error loading transactions: {e}")
            return []
    
    def get_total_spending(self, category=None, month=None, year=None):
        """Calculate total spending (withdrawals), optionally filtered by category, month, or year"""
        total = 0
        for transaction in self.transactions_data:
            # Filter by category if specified
            if category and transaction.get('Category', '').lower() != category.lower():
                continue
            
            # Filter by month if specified
            if month:
                transaction_date = transaction.get('Date', '')
                try:
                    # Extract month from date (format: YYYY-MM-DD)
                    trans_month = transaction_date.split('-')[1]
                    if month.zfill(2) != trans_month and month.lower() not in datetime.strptime(trans_month, '%m').strftime('%B').lower():
                        continue
                except:
                    continue
            
            # Filter by year if specified
            if year:
                transaction_date = transaction.get('Date', '')
                try:
                    trans_year = transaction_date.split('-')[0]
                    if str(year) != trans_year:
                        continue
                except:
                    continue
            
            # Sum up withdrawals (spending)
            withdrawal = float(transaction.get('Withdrawal(Dr)', 0))
            total += withdrawal
        
        return total
    
    def get_total_income(self, month=None, year=None):
        """Calculate total income (deposits)"""
        total = 0
        for transaction in self.transactions_data:
            # Filter by month if specified
            if month:
                transaction_date = transaction.get('Date', '')
                try:
                    trans_month = transaction_date.split('-')[1]
                    if month.zfill(2) != trans_month and month.lower() not in datetime.strptime(trans_month, '%m').strftime('%B').lower():
                        continue
                except:
                    continue
            
            # Filter by year if specified
            if year:
                transaction_date = transaction.get('Date', '')
                try:
                    trans_year = transaction_date.split('-')[0]
                    if str(year) != trans_year:
                        continue
                except:
                    continue
            
            # Sum up deposits (income)
            deposit = float(transaction.get('Deposit(Cr)', 0))
            total += deposit
        
        return total
    
    def get_transactions_by_category(self, category):
        """Get all transactions for a specific category"""
        return [t for t in self.transactions_data 
                if t.get('Category', '').lower() == category.lower()]
    
    def get_categories_summary(self):
        """Get spending summary by category"""
        categories = {}
        for transaction in self.transactions_data:
            category = transaction.get('Category', 'Unknown')
            withdrawal = float(transaction.get('Withdrawal(Dr)', 0))
            if withdrawal > 0:  # Only count actual spending
                categories[category] = categories.get(category, 0) + withdrawal
        
        return sorted(categories.items(), key=lambda x: x[1], reverse=True)
    
    def get_monthly_summary(self, year=None):
        """Get spending summary by month"""
        months = {}
        for transaction in self.transactions_data:
            date = transaction.get('Date', '')
            withdrawal = float(transaction.get('Withdrawal(Dr)', 0))
            
            if withdrawal > 0:  # Only count spending
                try:
                    # Extract year-month from date (YYYY-MM-DD)
                    date_parts = date.split('-')
                    if len(date_parts) >= 2:
                        trans_year, month = date_parts[0], date_parts[1]
                        
                        # Filter by year if specified
                        if year and str(year) != trans_year:
                            continue
                        
                        month_year = f"{trans_year}-{month}"
                        month_name = datetime.strptime(month, '%m').strftime('%B %Y')
                        months[month_name] = months.get(month_name, 0) + withdrawal
                except:
                    months['Unknown'] = months.get('Unknown', 0) + withdrawal
        
        return sorted(months.items())
    
    def search_transactions(self, search_term):
        """Search transactions by narration"""
        results = []
        search_lower = search_term.lower()
        for transaction in self.transactions_data:
            narration = transaction.get('Narration', '').lower()
            if search_lower in narration:
                results.append(transaction)
        return results
    
    def get_highest_expense(self):
        """Get the highest single expense"""
        if not self.transactions_data:
            return None
        
        highest = max(self.transactions_data, 
                     key=lambda x: float(x.get('Withdrawal(Dr)', 0)))
        
        withdrawal = float(highest.get('Withdrawal(Dr)', 0))
        if withdrawal > 0:
            return highest
        return None
    
    def get_recent_transactions(self, limit=5):
        """Get recent transactions sorted by date"""
        if not self.transactions_data:
            return []
        
        # Sort by date (assuming YYYY-MM-DD format)
        sorted_transactions = sorted(self.transactions_data, 
                                   key=lambda x: x.get('Date', ''), reverse=True)
        return sorted_transactions[:limit]
    
    def get_balance_info(self):
        """Get current balance from the most recent transaction"""
        if not self.transactions_data:
            return None
        
        # Get the transaction with the latest date
        latest_transaction = max(self.transactions_data, 
                               key=lambda x: x.get('Date', ''))
        return float(latest_transaction.get('Balance', 0))
    
    def get_transaction_context(self):
        """Get a summary of transaction data for AI context"""
        if not self.transactions_data:
            return "No transaction data available."
        
        # Get basic stats
        total_transactions = len(self.transactions_data)
        total_spending = self.get_total_spending()
        total_income = self.get_total_income()
        current_balance = self.get_balance_info()
        
        # Get top categories
        categories_summary = self.get_categories_summary()
        top_categories = categories_summary[:5] if categories_summary else []
        
        # Get recent transactions
        recent = self.get_recent_transactions(3)
        
        context = f"""Transaction Data Summary:
- Total transactions: {total_transactions}
- Total spending: ₹{total_spending:.2f}
- Total income: ₹{total_income:.2f}
- Current balance: ₹{current_balance:.2f}

Top spending categories:
"""
        for category, amount in top_categories:
            context += f"- {category}: ₹{amount:.2f}\n"
        
        context += "\nRecent transactions:\n"
        for transaction in recent:
            date = transaction.get('Date', '')
            withdrawal = float(transaction.get('Withdrawal(Dr)', 0))
            deposit = float(transaction.get('Deposit(Cr)', 0))
            narration = transaction.get('Narration', '')[:50]
            category = transaction.get('Category', '')
            
            if withdrawal > 0:
                context += f"- {date}: -₹{withdrawal:.2f} ({category}) - {narration}\n"
            elif deposit > 0:
                context += f"- {date}: +₹{deposit:.2f} - {narration}\n"
        
        return context

    def get_ai_response(self, query):
        """Get AI-powered response using OpenAI"""
        global client
        
        # Initialize client if not already done
        if client is None:
            client = init_openai_client()
        
        # If client initialization failed, use fallback
        if client is None:
            print("OpenAI client not available, using fallback")
            return self.get_simple_fallback(query)
        
        try:
            context = self.get_transaction_context()
            
            system_prompt = """You are a helpful financial assistant analyzing bank transaction data. 
            Be concise and direct in your responses. Keep answers short (1-3 sentences max).
            Use Indian Rupee (₹) format for amounts. Focus on the specific question asked.
            If asked about spending patterns, provide actionable insights.
            If the question cannot be answered from the transaction data, say so briefly."""
            
            user_prompt = f"""Based on this transaction data:

{context}

User question: {query}

Provide a concise, helpful answer based on the transaction data above."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,  # Keep responses short
                temperature=0.3  # More focused responses
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fallback to simple response
            return self.get_simple_fallback(query)

    def get_simple_fallback(self, query):
        """Simple fallback responses when AI fails"""
        query_lower = query.lower().strip()
        
        if any(word in query_lower for word in ['balance', 'current balance']):
            balance = self.get_balance_info()
            return f"Your current balance is ₹{balance:.2f}." if balance else "Balance information not available."
        
        elif any(word in query_lower for word in ['total', 'spent', 'spending']):
            total = self.get_total_spending()
            return f"Your total spending is ₹{total:.2f}."
        
        elif any(word in query_lower for word in ['income', 'earned']):
            income = self.get_total_income()
            return f"Your total income is ₹{income:.2f}."
        
        elif any(word in query_lower for word in ['categories', 'category']):
            categories = self.get_categories_summary()[:3]
            if categories:
                response = "Top spending categories: "
                response += ", ".join([f"{cat}: ₹{amt:.2f}" for cat, amt in categories])
                return response
            return "No category data available."
        
        else:
            return "I can help you with spending, income, balance, and category information. Please ask a specific question about your transactions."

    def process_query(self, query):
        """Process user query using AI first, fallback to simple responses"""
        if not self.transactions_data:
            return "No transaction data available. Please upload and process your bank statement first."
        
        # Try AI response first
        try:
            return self.get_ai_response(query)
        except Exception as e:
            print(f"AI processing failed: {e}")
            # Fallback to simple processing
            return self.get_simple_fallback(query)

# Global chatbot instance
chatbot = None

def init_chatbot():
    """Initialize chatbot with transaction data"""
    global chatbot
    json_path = Path("data/processed/categorized_transactions.json")
    chatbot = TransactionChatbot(json_path)
    return chatbot

def get_chatbot_response(message: str):
    """Get response from chatbot"""
    global chatbot
    
    # Initialize chatbot if not already done
    if not chatbot:
        init_chatbot()
    
    # Reload data to ensure we have the latest transactions
    chatbot.transactions_data = chatbot.load_transactions()
    
    if not chatbot.transactions_data:
        return "No transaction data available. Please upload and process your bank statement first."
    
    return chatbot.process_query(message)

def get_chatbot_stats():
    """Get basic statistics about the transaction data"""
    global chatbot
    
    if not chatbot:
        init_chatbot()
    
    # Reload data
    chatbot.transactions_data = chatbot.load_transactions()
    
    if not chatbot.transactions_data:
        return {
            'total_transactions': 0,
            'total_categories': 0,
            'categories': [],
            'total_spending': 0,
            'total_income': 0,
            'current_balance': 0
        }
    
    total_transactions = len(chatbot.transactions_data)
    categories = list(set([t.get('Category', '') for t in chatbot.transactions_data if t.get('Category')]))
    total_spending = chatbot.get_total_spending()
    total_income = chatbot.get_total_income()
    current_balance = chatbot.get_balance_info()
    
    return {
        'total_transactions': total_transactions,
        'total_categories': len(categories),
        'categories': sorted(categories),
        'total_spending': total_spending,
        'total_income': total_income,
        'current_balance': current_balance or 0
    }