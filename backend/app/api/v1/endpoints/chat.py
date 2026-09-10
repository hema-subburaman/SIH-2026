from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse
from app.services.ai_service import ai_service
from app.services.audit_service import audit_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(payload: ChatQueryRequest):
    """
    Conversational AI interface.
    Extracts intent, location, temporal slot, activity, and parameters,
    queries the meteorological engine, runs risk analysis, and localizes responses.
    """
    try:
        response = await ai_service.process_query(payload)
        await audit_service.log_weather_query(response)
        return response
    except Exception as e:
        logger.error(f"Error in chat query: {e}")
        raise HTTPException(status_code=500, detail=f"Conversational query processing failed: {str(e)}")
