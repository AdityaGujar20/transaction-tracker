import os
from datetime import datetime

import json
import pandas as pd

from langchain_community.chat_models import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from langchain.schema import HumanMessage, SystemMessage

from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

def load_categorized_data():
    file_path = os.path.join("..", "data", "processed", "categorized_bank_transactions_batch.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"🔴 File not found:\n  {file_path}")
    
    df = pd.read_csv(file_path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def summarize_for_llm(df, max_categories=7):
    summary = {}

    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    summary["months_covered"] = df["Month"].unique().tolist()
    summary["total_spent"] = round(df["Withdrawal(Dr)"].sum(), 2)
    summary["total_income"] = round(df["Deposit(Cr)"].sum(), 2)

    summary_df = df.groupby("Category").agg({
        "Withdrawal(Dr)": "sum",
        "Narration": "count"
    }).reset_index().sort_values("Withdrawal(Dr)", ascending=False)

    top_cats = summary_df.head(max_categories)
    summary["category_spending"] = top_cats.to_dict(orient="records")

    top_txns = df.sort_values("Withdrawal(Dr)", ascending=False).head(3)
    summary["top_transactions"] = top_txns[["Date", "Narration", "Withdrawal(Dr)", "Category"]].to_dict(orient="records")

    return summary


def build_prompt(summary_dict):
    return f"""
You're a financial assistant. Here's the user's spending 


Now:
1. Give a natural summary of their spending and income pattern.
2. Share 3–5 personalized ways they can save money based on top categories.
3. Call out anything unusual or interesting.

Format:
🧾 Spending Overview
📊 Top Categories
💡 Savings Tips
⚠️ Observations (if any)
Be clear, helpful, and friendly.
"""


def analyze_with_llm(summary_dict, openai_api_key):
    llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        model_name="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=500
    )

    messages = [
        SystemMessage(content="You are a helpful personal finance assistant."),
        HumanMessage(content=build_prompt(summary_dict))
    ]

    with get_openai_callback() as cb:
        response = llm(messages)
        print(f"\n📊 API usage: {cb.total_tokens} tokens | Cost: ${cb.total_cost:.4f}")

    return response.content.strip()


def main():
    print("📂 Loading categorized data...")
    
    try:
        df = load_categorized_data()
    except FileNotFoundError as e:
        print(e)
        return

    print("📈 Summarizing for LLM...")
    summary = summarize_for_llm(df)

    print("🔐 Checking API key...")
    openai_api_key = api_key
    if not openai_api_key.startswith("sk-"):
        print("❌ Please set a valid OpenAI API key in .env or directly in code.")
        return

    print("🤖 Sending to GPT-3.5 Turbo with 500 token limit...")
    result = analyze_with_llm(summary, openai_api_key)

    print("\n" + "=" * 60)
    print("✅ AI-Generated Spending Summary")
    print("=" * 60)
    print(result)
    print("\n🧠 Done.")
if __name__ == "__main__":
    main()
