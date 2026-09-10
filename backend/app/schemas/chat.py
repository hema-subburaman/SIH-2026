from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from app.schemas.risk import RiskLevel, RiskFactor


class ChatQueryRequest(BaseModel):
    message: str = Field(..., description="User query in English, Hindi, or Tamil")
    city: Optional[str] = "Chennai"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: Optional[str] = "en"  # en, hi, ta
    conversation_id: Optional[str] = None


class ExtractedEntities(BaseModel):
    intent: str
    location: Optional[str] = None
    target_date: Optional[str] = "today"
    target_time_slot: Optional[str] = "now"
    activity: Optional[str] = None
    weather_parameter: Optional[str] = None
    detected_language: str = "en"
    is_llm_enhanced: bool = False


class ChatQueryResponse(BaseModel):
    query: str
    language: str
    intent: str
    answer: str
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = None
    factors: List[RiskFactor] = []
    recommendation: Optional[str] = None
    location_used: str
    weather_summary: Optional[Dict[str, Any]] = None
    source: str
    provider: Optional[str] = None
    data_type: str = "meteorological_analysis"
    is_official: bool = False
    is_llm_enhanced: bool = False
    official_warning: Optional[Dict[str, Any]] = None
    timestamp: str
