from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Dict, Optional
import logging

from core.faq import (
    generate_financial_qa_json,
    ask_total_spending,
    ask_highest_spending_category,
    ask_total_income,
    ask_highest_single_expense,
    ask_category_spending,
    FinancialAnalyzer
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/get-answers")
def get_answers():
    """
    Generate complete financial analysis with all Q&A pairs
    """
    try:
        # Default path for categorized transactions
        json_file_path = "data/processed/categorized_transactions.json"
        output_path = "data/processed/financial_analysis_qa.json"
        
        # Check if source file exists
        source_path = Path(json_file_path)
        if not source_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Categorized transactions file not found. Please run the pipeline first to generate: {json_file_path}"
            )
        
        logger.info(f"Generating financial Q&A analysis from: {json_file_path}")
        
        # Generate complete Q&A analysis
        qa_data = generate_financial_qa_json(
            json_file_path=json_file_path,
            output_path=output_path
        )
        
        if not qa_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate financial analysis. Check if transaction data is valid."
            )
        
        return {
            "message": "Financial analysis completed successfully",
            "total_questions": len(qa_data.get("financial_analysis", {}).get("questions_and_answers", [])),
            "output_file": output_path,
            "data": qa_data
        }
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail="Categorized transactions file not found. Please run the pipeline first."
        )
    except Exception as e:
        logger.error(f"Error in financial analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/total-spending")
def get_total_spending():
    """Get total spending amount"""
    try:
        json_file_path = "data/processed/categorized_transactions.json"
        
        if not Path(json_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Categorized transactions file not found. Please run the pipeline first."
            )
        
        answer = ask_total_spending(json_file_path)
        
        return {
            "question": "What is my total spending?",
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"Error getting total spending: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/total-income")
def get_total_income():
    """Get total income amount"""
    try:
        json_file_path = "data/processed/categorized_transactions.json"
        
        if not Path(json_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Categorized transactions file not found. Please run the pipeline first."
            )
        
        answer = ask_total_income(json_file_path)
        
        return {
            "question": "What is my total income?",
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"Error getting total income: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/highest-expense")
def get_highest_expense():
    """Get highest single expense"""
    try:
        json_file_path = "data/processed/categorized_transactions.json"
        
        if not Path(json_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Categorized transactions file not found. Please run the pipeline first."
            )
        
        answer = ask_highest_single_expense(json_file_path)
        
        return {
            "question": "What is my highest single expense?",
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"Error getting highest expense: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/highest-category")
def get_highest_spending_category():
    """Get category with highest spending"""
    try:
        json_file_path = "data/processed/categorized_transactions.json"
        
        if not Path(json_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Categorized transactions file not found. Please run the pipeline first."
            )
        
        answer = ask_highest_spending_category(json_file_path)
        
        return {
            "question": "Which category do I spend the most on?",
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"Error getting highest spending category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/category-spending")
def get_category_spending():
    """Get spending breakdown by category"""
    try:
        json_file_path = "data/processed/categorized_transactions.json"
        
        if not Path(json_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Categorized transactions file not found. Please run the pipeline first."
            )
        
        answer = ask_category_spending(json_file_path)
        
        return {
            "question": "How much did I spend on each category?",
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"Error getting category spending: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
def get_financial_summary():
    """Get a quick financial summary"""
    try:
        json_file_path = "data/processed/categorized_transactions.json"
        
        if not Path(json_file_path).exists():
            raise HTTPException(
                status_code=404,
                detail="Categorized transactions file not found. Please run the pipeline first."
            )
        
        analyzer = FinancialAnalyzer(json_file_path)
        
        total_spending = analyzer.get_total_spending()
        total_income = analyzer.get_total_income()
        net_balance = analyzer.get_net_balance_change()
        highest_category = analyzer.get_highest_spending_category()
        transaction_counts = analyzer.get_transaction_count_by_type()
        
        return {
            "financial_summary": {
                "total_spending": f"₹{total_spending:,.2f}",
                "total_income": f"₹{total_income:,.2f}",
                "net_balance": f"₹{net_balance:,.2f}",
                "status": "profit" if net_balance >= 0 else "loss",
                "highest_spending_category": highest_category["category"],
                "highest_category_amount": f"₹{highest_category['amount']:,.2f}",
                "total_transactions": transaction_counts["total"],
                "income_transactions": transaction_counts["income_transactions"],
                "expense_transactions": transaction_counts["expense_transactions"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting financial summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))