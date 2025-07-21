import pdfplumber

import re
import pandas as pd

from datetime import datetime

from decimal import Decimal


def extract_bank_statement_table(pdf_path):
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
                        transaction = extract_transaction_details(line, lines[i:i+3])
                        if transaction:
                            transactions.append(transaction)
    
    # Convert to DataFrame
    df = pd.DataFrame(transactions)
    return df

def extract_transaction_details(line, context_lines):
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

def clean_and_format_data(df):
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

# Alternative approach using regex to parse the entire text
def extract_transactions_regex(pdf_path):
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

# Main execution function
def main():
    pdf_path = "../data/raw/kotak-bankstatement.pdf"  # Update with your PDF path
    
    print("Extracting transactions from bank statement...")
    
    # Try first method
    try:
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
    
    # Display results
    if not df.empty:
        print(f"\nSuccessfully extracted {len(df)} transactions")
        print("\nFirst 10 transactions:")
        print(df.head(10).to_string(index=False))
        
        # Save to CSV
        df.to_csv('../data/processed/bank_transactions.csv', index=False)
        print(f"\nTransactions saved to 'bank_transactions.csv'")
        
        # Display summary statistics
        print(f"\nSummary:")
        print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"Total withdrawals: ₹{df['Withdrawal(Dr)'].sum():,.2f}")
        print(f"Total deposits: ₹{df['Deposit(Cr)'].sum():,.2f}")
        print(f"Final balance: ₹{df['Balance'].iloc[-1]:,.2f}")
        
    else:
        print("No transactions found. Please check the PDF format.")

if __name__ == "__main__":
    main()
