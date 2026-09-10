from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.schemas.climate import ClimateTrendResponse
from app.services.climate_service import climate_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/history", response_model=ClimateTrendResponse)
async def get_climate_history(
    city: Optional[str] = Query(default="Chennai", description="City name"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    years: int = Query(default=10, ge=5, le=30, description="Historical timespan in years")
):
    """
    Retrieve historical climate observation and reanalysis trends.
    Clearly marks records as observational historical data (ERA5/WMO) rather than forecasts.
    """
    try:
        data = await climate_service.get_historical_trends(city=city, lat=lat, lon=lon, years=years)
        return data
    except Exception as e:
        logger.error(f"Error fetching climate trends: {e}")
        return ClimateTrendResponse(
            available=False,
            message="Historical climate data is temporarily unavailable.",
            location=city or "Chennai",
            latitude=lat or 0.0,
            longitude=lon or 0.0,
            data_points=[],
            source="Open-Meteo Historical Climate Service",
            provider="Open-Meteo Historical Climate Service",
            data_type="historical_reanalysis",
            is_official=False,
            citation="Historical climate data is temporarily unavailable."
        )
