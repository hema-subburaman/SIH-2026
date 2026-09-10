from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.schemas.alert import AlertsResponse
from app.services.alert_service import alert_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=AlertsResponse)
async def get_alerts(
    city: Optional[str] = Query(default="Chennai", description="City name"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude")
):
    """
    Retrieve active weather warnings and system risks.
    Strictly differentiates Official Warnings from System Weather Risks.
    """
    try:
        data = await alert_service.get_alerts_for_location(city=city, lat=lat, lon=lon)
        return data
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail="Alert retrieval failed")
