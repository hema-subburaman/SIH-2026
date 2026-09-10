from typing import Any, Dict, Optional
from app.ingestion.base_ingestor import BaseIngestor
from app.services.weather_service import weather_service
from app.ingestion.validator import MeteorologicalValidator
import logging

logger = logging.getLogger(__name__)


class WeatherIngestor(BaseIngestor):
    """Worker for real-time observational weather ingestion."""

    def __init__(self):
        super().__init__(
            name="Observational_Weather_Ingestor",
            provider="multi_provider",
            timeout_seconds=10.0,
            max_retries=2,
            backoff_factor=1.5,
        )

    async def fetch_and_parse(self, city: str = "Chennai", lat: Optional[float] = None, lon: Optional[float] = None, **kwargs) -> Any:
        weather_data = await weather_service.get_current_weather(city=city, lat=lat, lon=lon)
        obs_dict = {
            "temperature": weather_data.current.temperature,
            "humidity": weather_data.current.humidity,
            "wind_speed": weather_data.current.wind_speed,
            "pressure": weather_data.current.pressure,
        }
        is_valid, errors = MeteorologicalValidator.validate_observation(obs_dict)
        if not is_valid:
            raise ValueError(f"Observation failed validation: {errors}")
        return weather_data
