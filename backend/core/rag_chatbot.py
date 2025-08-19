# backend/core/rag_chatbot.py
import json
import pandas as pd
from datetime import datetime
import numpy as np
from typing import List, Dict, Any
import re
import os

class RAGTransactionChatbot:
    def __init__(self, data_file_path=None):
        """Initialize the RAG-based chatbot with transaction data"""
        if data_file_path is None:
            # Use processed data from your existing structure
            data_file_path = os.path.join(os.getcwd(), 'data', 'processed', 'categorized_transactions.json')
        
        self.data_file = data_file_path
        self.transactions = self.load_data()
        if self.transactions:
            self.df = pd.DataFrame(self.transactions)
            self.df['Date'] = pd.to_datetime(self.df['Date'])
            self.analytics = self.compute_analytics()
        else:
            self.df = pd.DataFrame()
            self.analytics = {}
    
    def load_data(self):
        """Load transaction data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"Successfully loaded {len(data)} transactions from {self.data_file}")
                    return data
            else:
                print(f"Data file {self.data_file} not found!")
                return []
        except FileNotFoundError:
            print(f"Data file {self.data_file} not found!")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {str(e)}")
            return []
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return []
    
    def compute_analytics(self):
        """Precompute various analytics for quick retrieval"""
        if self.df.empty:
            return {}
            
        analytics = {}
        
        # Overall statistics
        analytics['total_transactions'] = len(self.df)
        analytics['total_spent'] = self.df['Withdrawal(Dr)'].sum()
        analytics['total_received'] = self.df['Deposit(Cr)'].sum()
        analytics['current_balance'] = self.df.iloc[-1]['Balance'] if not self.df.empty else 0
        analytics['date_range'] = {
            'start': self.df['Date'].min().strftime('%Y-%m-%d'),
            'end': self.df['Date'].max().strftime('%Y-%m-%d')
        }
        
        # Add summary section for frontend compatibility
        analytics['summary'] = {
            'total_transactions': len(self.df),
            'total_debits': self.df['Withdrawal(Dr)'].sum(),
            'total_credits': self.df['Deposit(Cr)'].sum(),
            'current_balance': self.df.iloc[-1]['Balance'] if not self.df.empty else 0
        }
        
        # Category analytics
        analytics['categories'] = {}
        for category in self.df['Category'].unique():
            cat_data = self.df[self.df['Category'] == category]
            analytics['categories'][category] = {
                'total_spent': cat_data['Withdrawal(Dr)'].sum(),
                'total_received': cat_data['Deposit(Cr)'].sum(),
                'avg_spent': cat_data['Withdrawal(Dr)'].mean(),
                'avg_received': cat_data['Deposit(Cr)'].mean(),
                'transaction_count': len(cat_data),
                'max_transaction': cat_data['Withdrawal(Dr)'].max(),
                'min_transaction': cat_data['Withdrawal(Dr)'].min(),
                'spending_transactions': len(cat_data[cat_data['Withdrawal(Dr)'] > 0]),
                'credit_transactions': len(cat_data[cat_data['Deposit(Cr)'] > 0])
            }
        
        # Monthly analytics
        self.df['YearMonth'] = self.df['Date'].dt.to_period('M')
        analytics['monthly'] = {}
        for month in self.df['YearMonth'].unique():
            month_data = self.df[self.df['YearMonth'] == month]
            analytics['monthly'][str(month)] = {
                'total_spent': month_data['Withdrawal(Dr)'].sum(),
                'total_received': month_data['Deposit(Cr)'].sum(),
                'avg_spent': month_data['Withdrawal(Dr)'].mean(),
                'transaction_count': len(month_data),
                'net_flow': month_data['Deposit(Cr)'].sum() - month_data['Withdrawal(Dr)'].sum()
            }
        
        # Top transactions
        analytics['top_expenses'] = self.df.nlargest(10, 'Withdrawal(Dr)')[
            ['Date', 'Narration', 'Withdrawal(Dr)', 'Category']
        ].to_dict('records')
        
        analytics['top_credits'] = self.df.nlargest(10, 'Deposit(Cr)')[
            ['Date', 'Narration', 'Deposit(Cr)', 'Category']
        ].to_dict('records')
        
        return analytics
    
    def is_transaction_related(self, question: str) -> bool:
        """Check if the question is related to transaction/financial data"""
        question_lower = question.lower().strip()
        
        # Financial/transaction keywords that indicate relevance
        financial_keywords = [
            'transaction', 'transactions', 'payment', 'payments', 'transfer', 'transfers',
            'spend', 'spent', 'spending', 'expense', 'expenses', 'cost', 'costs',
            'credit', 'credited', 'debit', 'debited', 'deposit', 'withdrawal', 'withdraw',
            'money', 'amount', 'rupees', 'rs', '₹', 'balance', 'account',
            'total', 'sum', 'average', 'avg', 'mean', 'count', 'number', 'how many', 'how much',
            'top', 'highest', 'lowest', 'maximum', 'minimum', 'largest', 'smallest',
            'trend', 'monthly', 'yearly', 'over time', 'breakdown', 'summary',
            'food', 'dining', 'restaurant', 'healthcare', 'health', 'medical',
            'financial', 'finance', 'investment', 'transport', 'transportation', 'travel',
            'education', 'shopping', 'personal', 'care', 'transfer', 'refund',
            'miscellaneous', 'category', 'categories',
            'month', 'year', 'daily', 'weekly', 'period', 'date', 'time'
        ]
        
        # Check if question contains any financial keywords
        has_financial_keywords = any(keyword in question_lower for keyword in financial_keywords)
        
        # Check for date patterns
        has_date_pattern = bool(re.search(r'\d{4}(-\d{1,2})?', question_lower))
        
        # Non-financial topics that should be rejected
        non_financial_keywords = [
            'weather', 'climate', 'temperature', 'rain', 'sunny', 'cloudy',
            'recipe', 'cooking', 'ingredients', 'food recipe', 'how to cook',
            'movie', 'film', 'actor', 'actress', 'cinema', 'entertainment',
            'sports', 'football', 'cricket', 'basketball', 'game', 'match',
            'politics', 'government', 'election', 'politician', 'policy'
        ]
        
        # Check for non-financial topics
        has_non_financial = any(keyword in question_lower for keyword in non_financial_keywords)
        
        if has_non_financial:
            return False
        
        if has_financial_keywords or has_date_pattern:
            return True
        
        # Allow greetings and help questions
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        general_chat = ['how are you', 'what can you do', 'help', 'what is your name']
        
        if any(greeting in question_lower for greeting in greetings + general_chat):
            return True
        
        return False

    def understand_question(self, question: str) -> Dict[str, Any]:
        """Analyze question to understand intent and extract relevant information"""
        question_lower = question.lower().strip()
        
        intent = {
            'type': 'general',
            'category': None,
            'time_period': None,
            'metric': None,
            'transaction_type': None,
            'is_relevant': self.is_transaction_related(question)
        }
        
        # Check for greetings and help first
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        help_keywords = ['help', 'what can you do', 'capabilities', 'features']
        
        if any(greeting in question_lower for greeting in greetings):
            intent['type'] = 'greeting'
        elif any(keyword in question_lower for keyword in help_keywords):
            intent['type'] = 'help'
        elif any(word in question_lower for word in ['average', 'avg', 'mean']):
            intent['type'] = 'average'
        elif any(word in question_lower for word in ['total', 'sum', 'how much']):
            intent['type'] = 'total'
        elif any(word in question_lower for word in ['count', 'number', 'how many']):
            intent['type'] = 'count'
        elif any(word in question_lower for word in ['top', 'highest', 'largest', 'biggest']):
            intent['type'] = 'top'
        elif any(word in question_lower for word in ['balance', 'current']):
            intent['type'] = 'balance'
        elif any(word in question_lower for word in ['category', 'categories', 'breakdown']):
            intent['type'] = 'category_breakdown'
        
        # Detect category
        category_mapping = {
            'food': 'Food & Dining',
            'dining': 'Food & Dining',
            'restaurant': 'Food & Dining',
            'healthcare': 'Healthcare',
            'health': 'Healthcare',
            'medical': 'Healthcare',
            'financial': 'Financial Services',
            'finance': 'Financial Services',
            'transport': 'Transportation',
            'transportation': 'Transportation',
            'travel': 'Transportation',
            'education': 'Education',
            'shopping': 'Shopping',
            'personal': 'Personal Care',
            'care': 'Personal Care'
        }
        
        for keyword, actual_category in category_mapping.items():
            if keyword in question_lower:
                intent['category'] = actual_category
                break
        
        # Detect transaction type
        if any(word in question_lower for word in ['credited', 'credit', 'received', 'deposit']):
            intent['transaction_type'] = 'credit'
        elif any(word in question_lower for word in ['debited', 'debit', 'withdrawn', 'spent', 'expense']):
            intent['transaction_type'] = 'debit'
        
        return intent
    
    def generate_response(self, question: str) -> str:
        """Generate response based on question understanding"""
        intent = self.understand_question(question)
        intent['original_question'] = question
        
        # Check if question is relevant to transaction data
        if not intent['is_relevant']:
            return self.handle_out_of_context_question(question)
        
        try:
            if intent['type'] == 'greeting':
                return self.handle_greeting_question()
            elif intent['type'] == 'help':
                return self.handle_help_question()
            elif intent['type'] == 'average':
                return self.handle_average_question(intent)
            elif intent['type'] == 'total':
                return self.handle_total_question(intent)
            elif intent['type'] == 'count':
                return self.handle_count_question(intent)
            elif intent['type'] == 'top':
                return self.handle_top_question(intent)
            elif intent['type'] == 'balance':
                return self.handle_balance_question(intent)
            elif intent['type'] == 'category_breakdown':
                return self.handle_category_breakdown_question(intent)
            else:
                return self.handle_general_question(intent)
        except Exception as e:
            return f"I encountered an error processing your question: {str(e)}. Please try rephrasing your question."
    
    def handle_out_of_context_question(self, question: str) -> str:
        """Handle questions that are not related to transaction data"""
        return ("Sorry, I can only help with questions about your transaction data. "
               "Try asking about your spending, categories, balances, or transaction trends.")
    
    def handle_greeting_question(self) -> str:
        """Handle greeting questions"""
        return ("Hello! I'm your transaction analysis assistant. I can help you understand "
               "your financial data, spending patterns, and transaction history. What would you like to know?")
    
    def handle_help_question(self) -> str:
        """Handle help and capability questions"""
        return ("I can help you with:\n• Calculate averages, totals, and counts for any category\n"
               "• Show spending trends over time\n• Find top/bottom transactions\n"
               "• Analyze specific time periods\n• Break down spending by categories")
    
    def handle_average_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about averages"""
        category = intent.get('category')
        
        if category and category in self.analytics['categories']:
            cat_data = self.analytics['categories'][category]
            avg_amount = cat_data['avg_spent']
            return (f"Average spending for {category}: ₹{avg_amount:,.2f}\n"
                   f"Total transactions: {cat_data['spending_transactions']}\n"
                   f"Total spent: ₹{cat_data['total_spent']:,.2f}")
        else:
            avg_spending = self.df['Withdrawal(Dr)'].mean()
            return f"Overall average transaction amount: ₹{avg_spending:,.2f}"
    
    def handle_total_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about totals"""
        category = intent.get('category')
        
        if category and category in self.analytics['categories']:
            cat_data = self.analytics['categories'][category]
            return (f"Total for {category}:\n"
                   f"• Spent: ₹{cat_data['total_spent']:,.2f}\n"
                   f"• Received: ₹{cat_data['total_received']:,.2f}\n"
                   f"• Transactions: {cat_data['transaction_count']}")
        else:
            return (f"Overall totals:\n"
                   f"• Total spent: ₹{self.analytics['total_spent']:,.2f}\n"
                   f"• Total received: ₹{self.analytics['total_received']:,.2f}\n"
                   f"• Current balance: ₹{self.analytics['current_balance']:,.2f}")
    
    def handle_count_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about counts"""
        category = intent.get('category')
        
        if category and category in self.analytics['categories']:
            cat_data = self.analytics['categories'][category]
            return (f"Transaction count for {category}:\n"
                   f"• Total: {cat_data['transaction_count']}\n"
                   f"• Spending: {cat_data['spending_transactions']}\n"
                   f"• Credits: {cat_data['credit_transactions']}")
        else:
            return f"Total transactions: {self.analytics['total_transactions']}"
    
    def handle_top_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about top/highest values"""
        category = intent.get('category')
        
        if category:
            cat_transactions = [t for t in self.analytics['top_expenses'] if t['Category'] == category][:5]
            response = f"Top expenses in {category}:\n"
            for i, txn in enumerate(cat_transactions):
                response += f"{i+1}. ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}...\n"
        else:
            response = "Top 5 expenses overall:\n"
            for i, txn in enumerate(self.analytics['top_expenses'][:5]):
                response += f"{i+1}. ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}...\n"
        
        return response
    
    def handle_balance_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about balance"""
        return f"Current balance: ₹{self.analytics['current_balance']:,.2f}"
    
    def handle_category_breakdown_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about category breakdown"""
        response = "Category breakdown:\n"
        
        sorted_categories = sorted(
            self.analytics['categories'].items(),
            key=lambda x: x[1]['total_spent'],
            reverse=True
        )
        
        for category, data in sorted_categories:
            if data['total_spent'] > 0:
                response += f"• {category}: ₹{data['total_spent']:,.2f}\n"
        
        return response
    
    def handle_general_question(self, intent: Dict[str, Any]) -> str:
        """Handle general transaction-related questions"""
        return (f"Account Overview:\n"
               f"• Total transactions: {self.analytics['total_transactions']}\n"
               f"• Total spent: ₹{self.analytics['total_spent']:,.2f}\n"
               f"• Total received: ₹{self.analytics['total_received']:,.2f}\n"
               f"• Current balance: ₹{self.analytics['current_balance']:,.2f}")

# Global chatbot instance
_chatbot_instance = None

def get_chatbot():
    """Get or create chatbot instance"""
    global _chatbot_instance
    if _chatbot_instance is None:
        # Try to initialize with the correct path
        data_path = os.path.join(os.getcwd(), 'data', 'processed', 'categorized_transactions.json')
        print(f"Initializing chatbot with data from: {data_path}")
        _chatbot_instance = RAGTransactionChatbot(data_path)
    return _chatbot_instance