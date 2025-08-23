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

    def extract_date_info(self, question: str) -> Dict[str, Any]:
        """Extract date/time information from question"""
        question_lower = question.lower()
        
        # Month mapping
        months = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12',
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09', 
            'oct': '10', 'nov': '11', 'dec': '12'
        }
        
        date_info = {}
        
        # Extract month
        for month_name, month_num in months.items():
            if month_name in question_lower:
                date_info['month'] = month_num
                date_info['month_name'] = month_name.capitalize()
                break
        
        # Extract year (look for 4-digit years)
        year_match = re.search(r'\b(20\d{2})\b', question_lower)
        if year_match:
            date_info['year'] = year_match.group(1)
        
        # Extract week patterns
        if 'this week' in question_lower:
            date_info['period'] = 'this_week'
        elif 'last week' in question_lower:
            date_info['period'] = 'last_week'
        elif 'weekly' in question_lower:
            date_info['period'] = 'weekly'
        elif 'daily' in question_lower:
            date_info['period'] = 'daily'
        
        return date_info
    
    def extract_amount_info(self, question: str) -> Dict[str, Any]:
        """Extract amount/threshold information from question"""
        question_lower = question.lower()
        amount_info = {}
        
        # Extract amount patterns like "above 1000", "greater than 500", "between 100 and 500"
        above_match = re.search(r'(?:above|greater than|more than|over)\s*₹?(\d+(?:,\d+)*)', question_lower)
        below_match = re.search(r'(?:below|less than|under)\s*₹?(\d+(?:,\d+)*)', question_lower)
        between_match = re.search(r'between\s*₹?(\d+(?:,\d+)*)\s*(?:and|to)\s*₹?(\d+(?:,\d+)*)', question_lower)
        equals_match = re.search(r'(?:equals?|exactly)\s*₹?(\d+(?:,\d+)*)', question_lower)
        
        if between_match:
            amount_info['min_amount'] = float(between_match.group(1).replace(',', ''))
            amount_info['max_amount'] = float(between_match.group(2).replace(',', ''))
            amount_info['type'] = 'range'
        elif above_match:
            amount_info['min_amount'] = float(above_match.group(1).replace(',', ''))
            amount_info['type'] = 'above'
        elif below_match:
            amount_info['max_amount'] = float(below_match.group(1).replace(',', ''))
            amount_info['type'] = 'below'
        elif equals_match:
            amount_info['exact_amount'] = float(equals_match.group(1).replace(',', ''))
            amount_info['type'] = 'exact'
        
        return amount_info
    
    def extract_search_terms(self, question: str) -> List[str]:
        """Extract search terms from question"""
        question_lower = question.lower()
        search_terms = []
        
        # Look for quoted terms
        quoted_terms = re.findall(r'["\']([^"\']+)["\']', question)
        search_terms.extend(quoted_terms)
        
        # Look for common search patterns
        search_patterns = [
            r'(?:find|search|show|containing|with)\s+(?:all\s+)?(?:transactions?\s+)?(?:containing\s+|with\s+)?["\']?([^"\']+?)["\']?(?:\s|$)',
            r'payments?\s+to\s+["\']?([^"\']+?)["\']?(?:\s|$)',
            r'transactions?\s+from\s+["\']?([^"\']+?)["\']?(?:\s|$)'
        ]
        
        for pattern in search_patterns:
            matches = re.findall(pattern, question_lower)
            search_terms.extend(matches)
        
        # Clean up search terms
        cleaned_terms = []
        for term in search_terms:
            term = term.strip().strip('"\'')
            if term and len(term) > 1:
                cleaned_terms.append(term)
        
        return cleaned_terms
    
    def filter_by_date(self, df, date_info):
        """Filter dataframe by date information"""
        if df.empty:
            return df
            
        filtered_df = df.copy()
        
        if 'year' in date_info:
            filtered_df = filtered_df[filtered_df['Date'].dt.year == int(date_info['year'])]
        
        if 'month' in date_info:
            filtered_df = filtered_df[filtered_df['Date'].dt.strftime('%m') == date_info['month']]
        
        return filtered_df

    def understand_question(self, question: str) -> Dict[str, Any]:
        """Analyze question to understand intent and extract relevant information"""
        question_lower = question.lower().strip()
        
        intent = {
            'type': 'general',
            'category': None,
            'time_period': None,
            'metric': None,
            'transaction_type': None,
            'is_relevant': self.is_transaction_related(question),
            'date_info': self.extract_date_info(question),
            'amount_info': self.extract_amount_info(question),
            'search_terms': self.extract_search_terms(question)
        }
        
        # Check for greetings and help first
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        help_keywords = ['help', 'what can you do', 'capabilities', 'features']
        
        if any(greeting in question_lower for greeting in greetings):
            intent['type'] = 'greeting'
        elif any(keyword in question_lower for keyword in help_keywords):
            intent['type'] = 'help'
        # New question types
        elif any(word in question_lower for word in ['trend', 'trending', 'pattern', 'over time', 'growth', 'increase', 'decrease']):
            intent['type'] = 'trend'
        elif any(word in question_lower for word in ['compare', 'comparison', 'vs', 'versus', 'against']):
            intent['type'] = 'comparison'
        elif any(word in question_lower for word in ['find', 'search', 'containing', 'show me', 'payments to']):
            intent['type'] = 'search'
        elif any(word in question_lower for word in ['above', 'below', 'greater than', 'less than', 'between', 'over', 'under']):
            intent['type'] = 'threshold'
        elif any(word in question_lower for word in ['lowest', 'minimum', 'smallest', 'least', 'bottom']):
            intent['type'] = 'minimum'
        elif any(word in question_lower for word in ['percentage', 'percent', '%', 'ratio', 'proportion']):
            intent['type'] = 'percentage'
        elif any(word in question_lower for word in ['frequency', 'often', 'how many times', 'frequent']):
            intent['type'] = 'frequency'
        # Existing question types
        elif any(word in question_lower for word in ['average', 'avg', 'mean']):
            intent['type'] = 'average'
        elif any(word in question_lower for word in ['total', 'sum', 'how much']):
            intent['type'] = 'total'
        elif any(word in question_lower for word in ['count', 'number', 'how many']):
            intent['type'] = 'count'
        elif any(word in question_lower for word in ['top', 'highest', 'largest', 'biggest', 'maximum']):
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
            # New handlers
            elif intent['type'] == 'trend':
                return self.handle_trend_question(intent)
            elif intent['type'] == 'comparison':
                return self.handle_comparison_question(intent)
            elif intent['type'] == 'search':
                return self.handle_search_question(intent)
            elif intent['type'] == 'threshold':
                return self.handle_threshold_question(intent)
            elif intent['type'] == 'minimum':
                return self.handle_minimum_question(intent)
            elif intent['type'] == 'percentage':
                return self.handle_percentage_question(intent)
            elif intent['type'] == 'frequency':
                return self.handle_frequency_question(intent)
            # Existing handlers
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
        return ("I can help you with:\n"
               "• Calculate averages, totals, and counts for any category\n"
               "• Show spending trends and patterns over time\n"
               "• Find top/bottom transactions and minimum spending\n"
               "• Search transactions by description or merchant\n"
               "• Filter transactions by amount thresholds\n"
               "• Compare spending between different periods\n"
               "• Calculate percentages and ratios\n"
               "• Analyze frequency of transactions\n"
               "• Break down spending by categories and time periods")
    
    def handle_average_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about averages"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        if category:
            cat_filtered = filtered_df[filtered_df['Category'] == category]
            if cat_filtered.empty:
                period_str = self.get_period_string(date_info)
                return f"No {category} transactions found for {period_str}."
            
            avg_amount = cat_filtered['Withdrawal(Dr)'].mean()
            total_spent = cat_filtered['Withdrawal(Dr)'].sum()
            count = len(cat_filtered[cat_filtered['Withdrawal(Dr)'] > 0])
            period_str = self.get_period_string(date_info)
            
            return (f"Average spending for {category} {period_str}: ₹{avg_amount:,.2f}\n"
                   f"Total transactions: {count}\n"
                   f"Total spent: ₹{total_spent:,.2f}")
        else:
            avg_spending = filtered_df['Withdrawal(Dr)'].mean()
            period_str = self.get_period_string(date_info)
            return f"Average transaction amount {period_str}: ₹{avg_spending:,.2f}"
    
    def handle_total_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about totals"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        if category:
            cat_filtered = filtered_df[filtered_df['Category'] == category]
            if cat_filtered.empty:
                period_str = self.get_period_string(date_info)
                return f"No {category} transactions found for {period_str}."
            
            total_spent = cat_filtered['Withdrawal(Dr)'].sum()
            total_received = cat_filtered['Deposit(Cr)'].sum()
            count = len(cat_filtered)
            period_str = self.get_period_string(date_info)
            
            return (f"Total for {category} {period_str}:\n"
                   f"• Spent: ₹{total_spent:,.2f}\n"
                   f"• Received: ₹{total_received:,.2f}\n"
                   f"• Transactions: {count}")
        else:
            total_spent = filtered_df['Withdrawal(Dr)'].sum()
            total_received = filtered_df['Deposit(Cr)'].sum()
            period_str = self.get_period_string(date_info)
            
            return (f"Totals {period_str}:\n"
                   f"• Total spent: ₹{total_spent:,.2f}\n"
                   f"• Total received: ₹{total_received:,.2f}\n"
                   f"• Net flow: ₹{total_received - total_spent:,.2f}")
    
    def handle_count_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about counts"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        if category:
            cat_filtered = filtered_df[filtered_df['Category'] == category]
            if cat_filtered.empty:
                period_str = self.get_period_string(date_info)
                return f"No {category} transactions found for {period_str}."
            
            total_count = len(cat_filtered)
            spending_count = len(cat_filtered[cat_filtered['Withdrawal(Dr)'] > 0])
            credit_count = len(cat_filtered[cat_filtered['Deposit(Cr)'] > 0])
            period_str = self.get_period_string(date_info)
            
            return (f"Transaction count for {category} {period_str}:\n"
                   f"• Total: {total_count}\n"
                   f"• Spending: {spending_count}\n"
                   f"• Credits: {credit_count}")
        else:
            total_count = len(filtered_df)
            period_str = self.get_period_string(date_info)
            return f"Total transactions {period_str}: {total_count}"
    
    def handle_top_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about top/highest values"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        if category:
            cat_filtered = filtered_df[filtered_df['Category'] == category]
            if cat_filtered.empty:
                period_str = self.get_period_string(date_info)
                return f"No {category} transactions found for {period_str}."
            
            top_transactions = cat_filtered.nlargest(5, 'Withdrawal(Dr)')
            period_str = self.get_period_string(date_info)
            response = f"Top expenses in {category} {period_str}:\n"
            
            for i, (_, txn) in enumerate(top_transactions.iterrows()):
                if txn['Withdrawal(Dr)'] > 0:
                    response += f"{i+1}. ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}...\n"
        else:
            top_transactions = filtered_df.nlargest(5, 'Withdrawal(Dr)')
            period_str = self.get_period_string(date_info)
            response = f"Top 5 expenses {period_str}:\n"
            
            for i, (_, txn) in enumerate(top_transactions.iterrows()):
                if txn['Withdrawal(Dr)'] > 0:
                    response += f"{i+1}. ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}...\n"
        
        return response if response.count('\n') > 1 else f"No spending transactions found for the specified period."
    
    def handle_balance_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about balance"""
        return f"Current balance: ₹{self.analytics['current_balance']:,.2f}"
    
    def handle_category_breakdown_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about category breakdown"""
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        # Calculate category breakdown for filtered data
        category_spending = filtered_df.groupby('Category')['Withdrawal(Dr)'].sum().sort_values(ascending=False)
        
        period_str = self.get_period_string(date_info)
        response = f"Category breakdown {period_str}:\n"
        
        for category, amount in category_spending.items():
            if amount > 0:
                response += f"• {category}: ₹{amount:,.2f}\n"
        
        return response if len(category_spending) > 0 else f"No spending found for the specified period."
    
    def get_period_string(self, date_info: Dict[str, Any]) -> str:
        """Generate a human-readable period string from date info"""
        if not date_info:
            return "overall"
        
        parts = []
        if 'month_name' in date_info:
            parts.append(f"in {date_info['month_name']}")
        if 'year' in date_info:
            parts.append(date_info['year'])
        
        return " ".join(parts) if parts else "overall"

    def handle_trend_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about trends and patterns"""
        category = intent.get('category')
        
        # Get monthly data for trend analysis
        monthly_data = self.df.groupby(self.df['Date'].dt.to_period('M')).agg({
            'Withdrawal(Dr)': 'sum',
            'Deposit(Cr)': 'sum'
        }).reset_index()
        
        if len(monthly_data) < 2:
            return "Not enough data to show trends. Need at least 2 months of data."
        
        if category:
            cat_monthly = self.df[self.df['Category'] == category].groupby(
                self.df['Date'].dt.to_period('M')
            )['Withdrawal(Dr)'].sum().reset_index()
            
            if len(cat_monthly) < 2:
                return f"Not enough {category} data to show trends."
            
            latest = cat_monthly.iloc[-1]['Withdrawal(Dr)']
            previous = cat_monthly.iloc[-2]['Withdrawal(Dr)']
            change = ((latest - previous) / previous * 100) if previous > 0 else 0
            
            trend_direction = "increasing" if change > 5 else "decreasing" if change < -5 else "stable"
            
            response = f"{category} spending trend:\n"
            response += f"• Latest month: ₹{latest:,.2f}\n"
            response += f"• Previous month: ₹{previous:,.2f}\n"
            response += f"• Change: {change:+.1f}% ({trend_direction})\n\n"
            response += "Monthly breakdown:\n"
            
            for _, row in cat_monthly.tail(6).iterrows():
                response += f"• {row['Date']}: ₹{row['Withdrawal(Dr)']:,.2f}\n"
        else:
            latest = monthly_data.iloc[-1]['Withdrawal(Dr)']
            previous = monthly_data.iloc[-2]['Withdrawal(Dr)']
            change = ((latest - previous) / previous * 100) if previous > 0 else 0
            
            trend_direction = "increasing" if change > 5 else "decreasing" if change < -5 else "stable"
            
            response = f"Overall spending trend:\n"
            response += f"• Latest month: ₹{latest:,.2f}\n"
            response += f"• Previous month: ₹{previous:,.2f}\n"
            response += f"• Change: {change:+.1f}% ({trend_direction})\n\n"
            response += "Monthly breakdown:\n"
            
            for _, row in monthly_data.tail(6).iterrows():
                response += f"• {row['Date']}: ₹{row['Withdrawal(Dr)']:,.2f}\n"
        
        return response
    
    def handle_comparison_question(self, intent: Dict[str, Any]) -> str:
        """Handle comparison questions between periods"""
        # Extract months for comparison from the question
        question = intent.get('original_question', '').lower()
        
        # Simple month extraction for comparison
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november', 'december']
        
        found_months = [month for month in months if month in question]
        
        if len(found_months) >= 2:
            month1, month2 = found_months[0], found_months[1]
            
            # Get data for both months
            month1_data = self.df[self.df['Date'].dt.strftime('%B').str.lower() == month1]
            month2_data = self.df[self.df['Date'].dt.strftime('%B').str.lower() == month2]
            
            if month1_data.empty or month2_data.empty:
                return f"No data available for comparison between {month1.title()} and {month2.title()}."
            
            month1_spent = month1_data['Withdrawal(Dr)'].sum()
            month2_spent = month2_data['Withdrawal(Dr)'].sum()
            
            difference = month1_spent - month2_spent
            percentage_change = (difference / month2_spent * 100) if month2_spent > 0 else 0
            
            response = f"Comparison: {month1.title()} vs {month2.title()}\n"
            response += f"• {month1.title()}: ₹{month1_spent:,.2f}\n"
            response += f"• {month2.title()}: ₹{month2_spent:,.2f}\n"
            response += f"• Difference: ₹{difference:+,.2f}\n"
            response += f"• Change: {percentage_change:+.1f}%\n"
            
            if abs(percentage_change) > 20:
                response += f"• Significant {'increase' if percentage_change > 0 else 'decrease'} in spending!"
            
            return response
        else:
            # Default to comparing last two months
            monthly_data = self.df.groupby(self.df['Date'].dt.to_period('M'))['Withdrawal(Dr)'].sum()
            if len(monthly_data) < 2:
                return "Not enough data for comparison. Need at least 2 months."
            
            latest = monthly_data.iloc[-1]
            previous = monthly_data.iloc[-2]
            difference = latest - previous
            percentage_change = (difference / previous * 100) if previous > 0 else 0
            
            return (f"Last two months comparison:\n"
                   f"• Latest: ₹{latest:,.2f}\n"
                   f"• Previous: ₹{previous:,.2f}\n"
                   f"• Difference: ₹{difference:+,.2f} ({percentage_change:+.1f}%)")
    
    def handle_search_question(self, intent: Dict[str, Any]) -> str:
        """Handle search questions for specific transactions"""
        search_terms = intent.get('search_terms', [])
        date_info = intent.get('date_info', {})
        
        if not search_terms:
            return "Please specify what you want to search for (e.g., 'Amazon', 'ATM', 'Swiggy')."
        
        # Filter by date first
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        # Search in narration field
        search_results = pd.DataFrame()
        for term in search_terms:
            matches = filtered_df[filtered_df['Narration'].str.contains(term, case=False, na=False)]
            search_results = pd.concat([search_results, matches]).drop_duplicates()
        
        if search_results.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found containing '{', '.join(search_terms)}' {period_str}."
        
        # Sort by date (most recent first)
        search_results = search_results.sort_values('Date', ascending=False)
        
        total_spent = search_results['Withdrawal(Dr)'].sum()
        total_received = search_results['Deposit(Cr)'].sum()
        count = len(search_results)
        
        response = f"Found {count} transactions containing '{', '.join(search_terms)}':\n"
        response += f"• Total spent: ₹{total_spent:,.2f}\n"
        response += f"• Total received: ₹{total_received:,.2f}\n\n"
        response += "Recent transactions:\n"
        
        # Show top 10 results
        for _, txn in search_results.head(10).iterrows():
            date_str = txn['Date'].strftime('%Y-%m-%d')
            amount = txn['Withdrawal(Dr)'] if txn['Withdrawal(Dr)'] > 0 else txn['Deposit(Cr)']
            txn_type = "Dr" if txn['Withdrawal(Dr)'] > 0 else "Cr"
            response += f"• {date_str}: ₹{amount:,.2f} ({txn_type}) - {txn['Narration'][:40]}...\n"
        
        if len(search_results) > 10:
            response += f"... and {len(search_results) - 10} more transactions"
        
        return response
    
    def handle_threshold_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about amount thresholds"""
        amount_info = intent.get('amount_info', {})
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        if not amount_info:
            return "Please specify an amount threshold (e.g., 'above 1000', 'between 100 and 500')."
        
        # Filter by date first
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        # Filter by category if specified
        if category:
            filtered_df = filtered_df[filtered_df['Category'] == category]
            if filtered_df.empty:
                return f"No {category} transactions found for the specified period."
        
        # Apply amount filters
        if amount_info['type'] == 'above':
            result_df = filtered_df[filtered_df['Withdrawal(Dr)'] > amount_info['min_amount']]
        elif amount_info['type'] == 'below':
            result_df = filtered_df[filtered_df['Withdrawal(Dr)'] < amount_info['max_amount']]
        elif amount_info['type'] == 'range':
            result_df = filtered_df[
                (filtered_df['Withdrawal(Dr)'] >= amount_info['min_amount']) &
                (filtered_df['Withdrawal(Dr)'] <= amount_info['max_amount'])
            ]
        elif amount_info['type'] == 'exact':
            result_df = filtered_df[filtered_df['Withdrawal(Dr)'] == amount_info['exact_amount']]
        else:
            return "Could not understand the amount criteria."
        
        if result_df.empty:
            return f"No transactions found matching the amount criteria."
        
        count = len(result_df)
        total_amount = result_df['Withdrawal(Dr)'].sum()
        avg_amount = result_df['Withdrawal(Dr)'].mean()
        
        # Create description of criteria
        if amount_info['type'] == 'above':
            criteria = f"above ₹{amount_info['min_amount']:,.0f}"
        elif amount_info['type'] == 'below':
            criteria = f"below ₹{amount_info['max_amount']:,.0f}"
        elif amount_info['type'] == 'range':
            criteria = f"between ₹{amount_info['min_amount']:,.0f} and ₹{amount_info['max_amount']:,.0f}"
        else:
            criteria = f"exactly ₹{amount_info['exact_amount']:,.0f}"
        
        category_str = f" in {category}" if category else ""
        period_str = self.get_period_string(date_info)
        
        response = f"Transactions {criteria}{category_str} {period_str}:\n"
        response += f"• Count: {count} transactions\n"
        response += f"• Total amount: ₹{total_amount:,.2f}\n"
        response += f"• Average amount: ₹{avg_amount:,.2f}\n\n"
        
        # Show top transactions
        top_transactions = result_df.nlargest(5, 'Withdrawal(Dr)')
        response += "Top transactions:\n"
        for _, txn in top_transactions.iterrows():
            date_str = txn['Date'].strftime('%Y-%m-%d')
            response += f"• {date_str}: ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}...\n"
        
        return response
    
    def handle_minimum_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about minimum/lowest values"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        if category:
            cat_filtered = filtered_df[filtered_df['Category'] == category]
            if cat_filtered.empty:
                period_str = self.get_period_string(date_info)
                return f"No {category} transactions found for {period_str}."
            
            # Get minimum transactions (excluding zero amounts)
            spending_txns = cat_filtered[cat_filtered['Withdrawal(Dr)'] > 0]
            if spending_txns.empty:
                return f"No spending transactions found for {category}."
            
            min_transactions = spending_txns.nsmallest(5, 'Withdrawal(Dr)')
            period_str = self.get_period_string(date_info)
            response = f"Lowest expenses in {category} {period_str}:\n"
            
            for i, (_, txn) in enumerate(min_transactions.iterrows()):
                date_str = txn['Date'].strftime('%Y-%m-%d')
                response += f"{i+1}. ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}... ({date_str})\n"
        else:
            # Overall minimum transactions
            spending_txns = filtered_df[filtered_df['Withdrawal(Dr)'] > 0]
            if spending_txns.empty:
                return "No spending transactions found."
            
            min_transactions = spending_txns.nsmallest(5, 'Withdrawal(Dr)')
            period_str = self.get_period_string(date_info)
            response = f"Lowest expenses {period_str}:\n"
            
            for i, (_, txn) in enumerate(min_transactions.iterrows()):
                date_str = txn['Date'].strftime('%Y-%m-%d')
                response += f"{i+1}. ₹{txn['Withdrawal(Dr)']:,.2f} - {txn['Narration'][:30]}... ({date_str})\n"
        
        return response
    
    def handle_percentage_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about percentages and ratios"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        total_spending = filtered_df['Withdrawal(Dr)'].sum()
        total_income = filtered_df['Deposit(Cr)'].sum()
        
        if category:
            cat_spending = filtered_df[filtered_df['Category'] == category]['Withdrawal(Dr)'].sum()
            if total_spending > 0:
                percentage = (cat_spending / total_spending) * 100
                period_str = self.get_period_string(date_info)
                return (f"{category} spending {period_str}:\n"
                       f"• Amount: ₹{cat_spending:,.2f}\n"
                       f"• Percentage of total spending: {percentage:.1f}%\n"
                       f"• Total spending: ₹{total_spending:,.2f}")
            else:
                return "No spending data available for percentage calculation."
        else:
            # Overall ratios and percentages
            period_str = self.get_period_string(date_info)
            response = f"Financial ratios {period_str}:\n"
            
            if total_income > 0:
                savings_rate = ((total_income - total_spending) / total_income) * 100
                response += f"• Savings rate: {savings_rate:.1f}%\n"
                response += f"• Spending rate: {100 - savings_rate:.1f}%\n"
            
            response += f"• Total income: ₹{total_income:,.2f}\n"
            response += f"• Total spending: ₹{total_spending:,.2f}\n"
            response += f"• Net flow: ₹{total_income - total_spending:,.2f}\n\n"
            
            # Category percentages
            category_spending = filtered_df.groupby('Category')['Withdrawal(Dr)'].sum().sort_values(ascending=False)
            response += "Category breakdown:\n"
            
            for cat, amount in category_spending.head(5).items():
                if amount > 0:
                    percentage = (amount / total_spending) * 100
                    response += f"• {cat}: {percentage:.1f}% (₹{amount:,.2f})\n"
            
            return response
    
    def handle_frequency_question(self, intent: Dict[str, Any]) -> str:
        """Handle questions about transaction frequency"""
        category = intent.get('category')
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        if category:
            cat_filtered = filtered_df[filtered_df['Category'] == category]
            if cat_filtered.empty:
                period_str = self.get_period_string(date_info)
                return f"No {category} transactions found for {period_str}."
            
            # Calculate frequency metrics
            total_days = (filtered_df['Date'].max() - filtered_df['Date'].min()).days + 1
            transaction_count = len(cat_filtered)
            spending_count = len(cat_filtered[cat_filtered['Withdrawal(Dr)'] > 0])
            
            avg_per_month = transaction_count / (total_days / 30.44) if total_days > 0 else 0
            
            period_str = self.get_period_string(date_info)
            response = f"{category} transaction frequency {period_str}:\n"
            response += f"• Total transactions: {transaction_count}\n"
            response += f"• Spending transactions: {spending_count}\n"
            response += f"• Average per month: {avg_per_month:.1f} transactions\n"
            
            # Most frequent amounts
            frequent_amounts = cat_filtered['Withdrawal(Dr)'].value_counts().head(3)
            if not frequent_amounts.empty:
                response += "\nMost frequent amounts:\n"
                for amount, count in frequent_amounts.items():
                    if amount > 0:
                        response += f"• ₹{amount:,.2f}: {count} times\n"
        else:
            # Overall frequency analysis
            total_days = (filtered_df['Date'].max() - filtered_df['Date'].min()).days + 1
            transaction_count = len(filtered_df)
            
            avg_per_day = transaction_count / total_days if total_days > 0 else 0
            avg_per_month = transaction_count / (total_days / 30.44) if total_days > 0 else 0
            
            period_str = self.get_period_string(date_info)
            response = f"Transaction frequency {period_str}:\n"
            response += f"• Total transactions: {transaction_count}\n"
            response += f"• Average per day: {avg_per_day:.1f}\n"
            response += f"• Average per month: {avg_per_month:.1f}\n\n"
            
            # Category frequency
            category_counts = filtered_df['Category'].value_counts().head(5)
            response += "Most frequent categories:\n"
            for category, count in category_counts.items():
                response += f"• {category}: {count} transactions\n"
        
        return response

    def handle_general_question(self, intent: Dict[str, Any]) -> str:
        """Handle general transaction-related questions"""
        date_info = intent.get('date_info', {})
        
        # Filter data by date if specified
        filtered_df = self.filter_by_date(self.df, date_info)
        
        if filtered_df.empty:
            period_str = self.get_period_string(date_info)
            return f"No transactions found for {period_str}."
        
        total_spent = filtered_df['Withdrawal(Dr)'].sum()
        total_received = filtered_df['Deposit(Cr)'].sum()
        total_transactions = len(filtered_df)
        period_str = self.get_period_string(date_info)
        
        return (f"Account Overview {period_str}:\n"
               f"• Total transactions: {total_transactions}\n"
               f"• Total spent: ₹{total_spent:,.2f}\n"
               f"• Total received: ₹{total_received:,.2f}\n"
               f"• Net flow: ₹{total_received - total_spent:,.2f}")

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