from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.schemas.weather import NormalizedWeatherResponse, DetailedForecastResponse
from app.schemas.forecast_common import ModelComparisonResponse
from app.providers.base import UpstreamRateLimitError
from app.services.weather_service import weather_service
from app.services.forecast_service import forecast_service
from app.services.model_comparison_service import model_comparison_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/current", response_model=NormalizedWeatherResponse)
async def get_current_weather(
    city: Optional[str] = Query(default="Chennai", description="City name (e.g. Chennai, Delhi, Mumbai)"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    provider: Optional[str] = Query(default=None, description="openweather or open_meteo")
):
    """Retrieve normalized real-time weather observations."""
    try:
        data = await weather_service.get_current_weather(city=city, lat=lat, lon=lon, preferred_provider=provider)
        return data
    except UpstreamRateLimitError as e:
        logger.warning(f"Upstream rate limit in /current: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "temporarily_unavailable",
                "provider": e.provider,
                "message": "Open-Meteo meteorological service is temporarily rate-limited. Please retry shortly.",
                "retry_after": e.retry_after or 60,
            },
            headers={"Retry-After": str(e.retry_after or 60)}
        )
    except Exception as e:
        logger.error(f"Error in /current: {e}")
        raise HTTPException(status_code=500, detail=f"Weather retrieval error: {str(e)}")


@router.get("/forecast", response_model=NormalizedWeatherResponse)
async def get_forecast(
    city: Optional[str] = Query(default="Chennai", description="City name"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    days: int = Query(default=5, ge=1, le=7, description="Forecast days"),
    provider: Optional[str] = Query(default=None, description="openweather or open_meteo")
):
    """Retrieve normalized 5-to-7 day numerical forecast data."""
    try:
        data = await weather_service.get_forecast(city=city, lat=lat, lon=lon, days=days, preferred_provider=provider)
        return data
    except UpstreamRateLimitError as e:
        logger.warning(f"Upstream rate limit in /forecast: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "temporarily_unavailable",
                "provider": e.provider,
                "message": "Open-Meteo meteorological service is temporarily rate-limited. Please retry shortly.",
                "retry_after": e.retry_after or 60,
            },
            headers={"Retry-After": str(e.retry_after or 60)}
        )
    except Exception as e:
        logger.error(f"Error in /forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast retrieval error: {str(e)}")


@router.get("/forecast/detailed", response_model=DetailedForecastResponse)
async def get_detailed_forecast(
    city: Optional[str] = Query(default="Chennai", description="City name"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    days: int = Query(default=7, ge=1, le=7, description="Forecast days")
):
    """Retrieve detailed structured daily aggregations, time-of-day breakdowns, and weekend outlook."""
    try:
        data = await forecast_service.get_detailed_forecast(city=city, lat=lat, lon=lon, days=days)
        return data
    except UpstreamRateLimitError as e:
        logger.warning(f"Upstream rate limit in /forecast/detailed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "temporarily_unavailable",
                "provider": e.provider,
                "message": "Open-Meteo meteorological service is temporarily rate-limited. Please retry shortly.",
                "retry_after": e.retry_after or 60,
            },
            headers={"Retry-After": str(e.retry_after or 60)}
        )
    except Exception as e:
        logger.error(f"Error in /forecast/detailed: {e}")
        raise HTTPException(status_code=500, detail=f"Detailed forecast retrieval error: {str(e)}")


@router.get("/forecast/compare", response_model=ModelComparisonResponse)
async def compare_forecast_models(
    city: Optional[str] = Query(default="Chennai", description="Target city name"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    days: int = Query(default=5, ge=1, le=7, description="Forecast days to compare")
):
    """
    Compare multi-model forecasts (Open-Meteo, NOAA GFS, WRF Meso-scale, OpenWeather).
    Provides deterministic model agreement score, variable-level divergences, and explainable consensus.
    """
    try:
        resolved_lat, resolved_lon, resolved_name, _, _ = await weather_service.open_meteo.resolve_coordinates(city, lat, lon)
        return await model_comparison_service.compare_forecasts(
            lat=resolved_lat, lon=resolved_lon, location_name=resolved_name, days=days
        )
    except Exception as e:
        logger.error(f"Error in /forecast/compare: {e}")
        raise HTTPException(status_code=500, detail=f"Model comparison error: {str(e)}")


@router.get("/location", response_model=List[Dict[str, Any]])
async def search_locations(
    query: str = Query(..., min_length=1, description="Location search query")
):
    """Search and autocomplete locations with geographic coordinates."""
    try:
        results = await weather_service.search_locations(query)
        return results
    except Exception as e:
        logger.error(f"Error searching location: {e}")
        raise HTTPException(status_code=500, detail="Failed to search location")
