import pdfplumber
import pandas as pd

import re
import json
from datetime import datetime
from decimal import Decimal


def extract_bank_statement_table(pdf_path):
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    date_pattern = r'(\d{2}-\d{2}-\d{4})'
                    date_match = re.search(date_pattern, line)
                    if date_match:
                        if 'Date' in line or 'Narration' in line:
                            continue
                        transaction = extract_transaction_details(line, lines[i:i+3])
                        if transaction:
                            transactions.append(transaction)
    return pd.DataFrame(transactions)

def extract_transaction_details(line, context_lines):
    try:
        date_pattern = r'(\d{2}-\d{2}-\d{4})'
        date_match = re.search(date_pattern, line)
        if not date_match:
            return None
        amounts = re.findall(r'([\d,]+\.?\d*)\s*\((Dr|Cr)\)', line)
        if len(amounts) < 2:
            return None
        narration_start = date_match.end()
        first_amount_pos = line.find(amounts[0][0])
        narration = line[narration_start:first_amount_pos].strip()
        withdrawal_amount = deposit_amount = 0.0
        first_amount = float(amounts[0][0].replace(',', ''))
        if amounts[0][1] == 'Dr':
            withdrawal_amount = first_amount
        else:
            deposit_amount = first_amount
        balance = float(amounts[-1][0].replace(',', ''))
        return {
            'Date': date_match.group(1),
            'Narration': narration.strip(),
            'Withdrawal(Dr)': withdrawal_amount if withdrawal_amount > 0 else None,
            'Deposit(Cr)': deposit_amount if deposit_amount > 0 else None,
            'Balance': balance
        }
    except Exception as e:
        print(f"Error processing line: {line[:50]}... Error: {str(e)}")
        return None

def clean_and_format_data(df):
    if df.empty:
        return df
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df = df.sort_values('Date').reset_index(drop=True)
    df['Withdrawal(Dr)'] = df['Withdrawal(Dr)'].fillna(0)
    df['Deposit(Cr)'] = df['Deposit(Cr)'].fillna(0)
    return df

def extract_transactions_regex(pdf_path):
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    pattern = r'''
        (\d{2}-\d{2}-\d{4})\s+          # Date
        (.+?)\s+                         # Narration
        ([\d,]+\.?\d*)\s*\((Dr|Cr)\)\s+  # Withdrawal/Deposit amount
        ([\d,]+\.?\d*)\s*\(Cr\)          # Balance
    '''
    matches = re.findall(pattern, full_text, re.VERBOSE | re.MULTILINE)
    for date_str, narration, amount, dr_cr, balance in matches:
        withdrawal = float(amount.replace(',', '')) if dr_cr == 'Dr' else 0
        deposit = float(amount.replace(',', '')) if dr_cr == 'Cr' else 0
        transactions.append({
            'Date': date_str,
            'Narration': narration.strip(),
            'Withdrawal(Dr)': withdrawal if withdrawal > 0 else None,
            'Deposit(Cr)': deposit if deposit > 0 else None,
            'Balance': float(balance.replace(',', ''))
        })
    return pd.DataFrame(transactions)

def extract_pdf_to_json(pdf_path):
    """Main function to extract PDF and return JSON data"""
    try:
        print("\n" + "="*60)
        print("📄 PDF EXTRACTION")
        print("="*60)
        
        df = extract_bank_statement_table(pdf_path)
        df = clean_and_format_data(df)
        if df.empty:
            print("First method failed, trying alternative approach...")
            df = extract_transactions_regex(pdf_path)
            df = clean_and_format_data(df)
    except Exception as e:
        print(f"Error: {e}")
        print("Trying alternative approach...")
        df = extract_transactions_regex(pdf_path)
        df = clean_and_format_data(df)
    
    if not df.empty:
        # Convert DataFrame to JSON format
        # Handle datetime serialization
        df_copy = df.copy()
        df_copy['Date'] = df_copy['Date'].dt.strftime('%Y-%m-%d')
        
        # Convert to list of dictionaries
        transactions_json = df_copy.to_dict('records')
        
        print(f"✅ {len(transactions_json)} transactions extracted successfully")
        print("="*60)
        return transactions_json
    else:
        print("❌ No transactions found.")
        return []

## For testing (Uncomment the below code when you want to see the output of this code)
# print(extract_pdf_to_json(pdf_path="../data/raw/kotak-bankstatement-1y-1-4.pdf"))