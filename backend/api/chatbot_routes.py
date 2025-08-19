# backend/api/chatbot_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from core.rag_chatbot import get_chatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Pydantic models for request/response
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    intent: Dict[str, Any]
    success: bool

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    """
    Chat with the RAG-based transaction bot
    """
    try:
        # Get chatbot instance
        chatbot = get_chatbot()
        
        if not chatbot.df.empty:
            # Understand the question
            intent = chatbot.understand_question(chat_message.message)
            
            # Generate response
            response = chatbot.generate_response(chat_message.message)
            
            return ChatResponse(
                response=response,
                intent=intent,
                success=True
            )
        else:
            return ChatResponse(
                response="Sorry, I don't have any transaction data to analyze. Please upload your transaction data first.",
                intent={"type": "error", "is_relevant": False},
                success=False
            )
            
    except Exception as e:
        logging.error(f"Chatbot error: {str(e)}")
        return ChatResponse(
            response="I'm sorry, I encountered an error while processing your request. Please try again.",
            intent={"type": "error", "is_relevant": False},
            success=False
        )

@router.get("/analytics")
async def get_analytics():
    """
    Get precomputed analytics for the chatbot
    """
    try:
        chatbot = get_chatbot()
        
        if not chatbot.df.empty:
            logging.info(f"Analytics retrieved successfully with {len(chatbot.df)} transactions")
            return {
                "analytics": chatbot.analytics,
                "success": True
            }
        else:
            logging.warning("No transaction data available for analytics")
            return {
                "analytics": {
                    "summary": {
                        "total_transactions": 0,
                        "total_debits": 0,
                        "total_credits": 0,
                        "current_balance": 0
                    }
                },
                "success": False,
                "message": "No transaction data available"
            }
            
    except Exception as e:
        logging.error(f"Analytics error: {str(e)}")
        return {
            "analytics": {
                "summary": {
                    "total_transactions": 0,
                    "total_debits": 0,
                    "total_credits": 0,
                    "current_balance": 0
                }
            },
            "success": False,
            "error": str(e)
        }

@router.get("/status")
async def get_chatbot_status():
    """
    Get chatbot status and data availability
    """
    try:
        chatbot = get_chatbot()
        
        return {
            "status": "active",
            "data_available": not chatbot.df.empty,
            "total_transactions": len(chatbot.df) if not chatbot.df.empty else 0,
            "date_range": chatbot.analytics.get('date_range', {}) if not chatbot.df.empty else {},
            "categories": list(chatbot.analytics.get('categories', {}).keys()) if not chatbot.df.empty else []
        }
        
    except Exception as e:
        logging.error(f"Status error: {str(e)}")
        return {
            "status": "error",
            "data_available": False,
            "error": str(e)
        }

@router.post("/reload-data")
async def reload_chatbot_data():
    """
    Reload transaction data for the chatbot
    """
    try:
        import os
        
        # Check if data file exists
        data_path = os.path.join(os.getcwd(), 'data', 'processed', 'categorized_transactions.json')
        logging.info(f"Checking for data file at: {data_path}")
        
        if not os.path.exists(data_path):
            logging.error(f"Data file not found at {data_path}")
            raise HTTPException(status_code=404, detail=f"Data file not found at {data_path}")
        
        # Reset the global instance to force reload
        from core.rag_chatbot import get_chatbot
        import core.rag_chatbot as chatbot_module
        chatbot_module._chatbot_instance = None
        logging.info("Global chatbot instance reset")
        
        # Get new instance
        chatbot = get_chatbot()
        logging.info(f"New chatbot instance created with {len(chatbot.df)} transactions")
        
        return {
            "success": True,
            "message": "Data reloaded successfully",
            "total_transactions": len(chatbot.df) if not chatbot.df.empty else 0,
            "data_path": data_path,
            "analytics_available": bool(chatbot.analytics)
        }
        
    except Exception as e:
        logging.error(f"Reload data error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Error reloading data: {str(e)}"
        }