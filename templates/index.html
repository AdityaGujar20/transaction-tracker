import pdfplumber
import pandas as pd
import re
import os
from decimal import Decimal
from datetime import datetime

def extract_bank_statement_table(pdf_path):
    """
    Extract transaction table from bank statement PDF
    """
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
                        date_str = date_match.group(1)
                        
                        if 'Date' in line or 'Narration' in line:
                            continue
                            
                        transaction = extract_transaction_details(line, lines[i:i+3])
                        if transaction:
                            transactions.append(transaction)
    
    df = pd.DataFrame(transactions)
    return df

def extract_transaction_details(line, context_lines):
    """
    Extract individual transaction details from a line
    """
    try:
        date_pattern = r'(\d{2}-\d{2}-\d{4})'
        date_match = re.search(date_pattern, line)
        if not date_match:
            return None
            
        date_str = date_match.group(1)
        
        # Amount patterns
        amount_pattern = r'([\d,]+\.?\d*)\s*\((Dr|Cr)\)'
        amounts = re.findall(amount_pattern, line)
        
        if len(amounts) < 2:
            return None
            
        # Extract narration
        narration_start = date_match.end()
        first_amount_pos = line.find(amounts[0][0])
        narration = line[narration_start:first_amount_pos].strip()
        
        # Extract reference number
        ref_pattern = r'([A-Z0-9\-]+)\s*(?=[\d,]+\.?\d*\s*\()'
        ref_match = re.search(ref_pattern, narration)
        ref_no = ref_match.group(1) if ref_match else ""
        
        if ref_no:
            narration = narration.replace(ref_no, "").strip()
        
        # Parse amounts
        withdrawal_amount = 0.0
        deposit_amount = 0.0
        balance = 0.0
        
        first_amount = float(amounts[0][0].replace(',', ''))
        if amounts[0][1] == 'Dr':
            withdrawal_amount = first_amount
        else:
            deposit_amount = first_amount
            
        balance = float(amounts[-1][0].replace(',', ''))
        
        return {
            'Date': date_str,
            'Narration': narration.strip(),
            'Chq/Ref No': ref_no,
            'Withdrawal(Dr)': withdrawal_amount if withdrawal_amount > 0 else 0,
            'Deposit(Cr)': deposit_amount if deposit_amount > 0 else 0,
            'Balance': balance
        }
        
    except Exception as e:
        print(f"Error processing line: {line[:50]}... Error: {str(e)}")
        return None

def clean_and_format_data(df):
    """
    Clean and format the extracted data
    """
    if df.empty:
        return df
        
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df = df.sort_values('Date').reset_index(drop=True)
    df['Withdrawal(Dr)'] = df['Withdrawal(Dr)'].fillna(0)
    df['Deposit(Cr)'] = df['Deposit(Cr)'].fillna(0)
    
    return df
