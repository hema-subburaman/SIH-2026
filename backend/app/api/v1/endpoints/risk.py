from fastapi import APIRouter, HTTPException
from app.schemas.risk import RiskAnalysisRequest, RiskAnalysisResponse
from app.services.risk_engine import risk_engine
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=RiskAnalysisResponse)
async def analyze_risk(payload: RiskAnalysisRequest):
    """
    Evaluates meteorological factors against specific activity tolerance profiles.
    Returns calculated composite risk level, explainable factors, and actionable recommendations.
    """
    try:
        response = risk_engine.analyze(
            activity=payload.activity,
            temperature=payload.temperature,
            humidity=payload.humidity,
            wind_speed=payload.wind_speed,
            condition=payload.condition,
            pop=payload.pop or 0.0,
            feels_like=payload.feels_like,
            visibility=payload.visibility,
            target_time=payload.target_time or "Current",
            language=payload.language or "en",
            custom_scenario=payload.custom_scenario
        )
        return response
    except Exception as e:
        logger.error(f"Error analyzing risk: {e}")
        raise HTTPException(status_code=500, detail=f"Risk engine evaluation failed: {str(e)}")
