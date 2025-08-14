from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path

from datetime import datetime
import sys
import os

# Add the parent directory to sys.path to import the chatbot module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import chatbot functions (using simple version for now)
try:
    from core.chatbot import get_chatbot_response, get_chatbot_stats
except ImportError:
    # Fallback to simple version if OpenAI has issues
    from core.chatbot_simple import get_chatbot_response, get_chatbot_stats

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """
    Process a chat message and return chatbot response
    """
    try:
        if not chat_message.message or not chat_message.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Get response from chatbot
        response = get_chatbot_response(chat_message.message.strip())
        
        return ChatResponse(
            response=response,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")

@router.get("/stats")
async def get_chatbot_statistics():
    """
    Get basic statistics about the transaction data
    """
    try:
        stats = get_chatbot_stats()
        return JSONResponse(content=stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting chatbot stats: {str(e)}")

@router.get("/health")
async def chatbot_health():
    """
    Check if chatbot service is healthy and data is available
    """
    try:
        json_path = Path("data/processed/categorized_transactions.json")
        
        if not json_path.exists():
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "message": "Transaction data not found. Please upload and process your bank statement first.",
                    "data_available": False
                },
                status_code=200
            )
        
        stats = get_chatbot_stats()
        
        return JSONResponse(
            content={
                "status": "healthy",
                "message": "Chatbot is ready to answer your questions",
                "data_available": True,
                "transactions_loaded": stats["total_transactions"]
            }
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Error checking chatbot health: {str(e)}",
                "data_available": False
            },
            status_code=500
        )