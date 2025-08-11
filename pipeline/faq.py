import pandas as pd
import numpy as np

def load_transaction_data(csv_path):
    return pd.read_csv(csv_path)

def get_total_spending(df):
    total = df['Withdrawal(Dr)'].sum()
    return f"What is the total spending?\nTotal spending: ₹{total:,.2f}"

def get_highest_spending_category(df):
    category_spending = df.groupby('Category')['Withdrawal(Dr)'].sum().sort_values(ascending=False)
    highest_category = category_spending.index[0]
    amount = category_spending.iloc[0]
    return f"Which category has the highest spending?\nHighest spending category: {highest_category} (₹{amount:,.2f})"

def get_total_income(df):
    total = df['Deposit(Cr)'].sum()
    return f"What is the total income?\nTotal income: ₹{total:,.2f}"

def get_highest_expense(df):
    max_expense = df['Withdrawal(Dr)'].max()
    transaction = df[df['Withdrawal(Dr)'] == max_expense].iloc[0]
    return f"What is the highest single expense?\nHighest single expense: ₹{max_expense:,.2f} ({transaction['Narration']})"

def get_category_spending(df):
    category_spending = df.groupby('Category')['Withdrawal(Dr)'].sum().sort_values(ascending=False)
    result = "How much was spent in each category?\nCategory-wise spending:\n"
    for category, amount in category_spending.items():
        result += f"- {category}: ₹{amount:,.2f}\n"
    return result

def run_faq(csv_path):
    df = load_transaction_data(csv_path)
    
    # Generate all FAQ answers
    answers = {
        "total_spending": get_total_spending(df),
        "highest_category": get_highest_spending_category(df),
        "total_income": get_total_income(df),
        "highest_expense": get_highest_expense(df),
        "category_spending": get_category_spending(df)
    }
    
    return answers

if __name__ == "__main__":
    csv_path = "sample-test-output/categorized_bank_transactions_batch.csv"
    answers = run_faq(csv_path)
    for question, answer in answers.items():
        print(f"\n{answer}")

# Remove this duplicate line
# answers = run_faq('sample-test-output/categorized_bank_transactions_batch.csv')
