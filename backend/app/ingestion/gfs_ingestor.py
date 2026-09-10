from typing import Any, Dict, Optional, List
from app.ingestion.base_ingestor import BaseIngestor
from app.providers.gfs_provider import GFSProvider
from app.ingestion.validator import MeteorologicalValidator
from app.schemas.forecast_common import CommonModelForecastResponse
import logging

logger = logging.getLogger(__name__)


class GFSIngestor(BaseIngestor):
    """Worker for NOAA GFS 0.25° NWP numerical forecast ingestion."""

    def __init__(self):
        super().__init__(
            name="NOAA_GFS_Ingestor",
            provider="gfs",
            timeout_seconds=15.0,
            max_retries=2,
            backoff_factor=1.5,
        )
        self.provider_instance = GFSProvider()

    async def fetch_and_parse(self, lat: float = 13.0827, lon: float = 80.2707, days: int = 5, **kwargs) -> CommonModelForecastResponse:
        result = await self.provider_instance.get_common_forecast(lat=lat, lon=lon, days=days)
        if not result.available:
            raise RuntimeError(f"GFS Ingestion: {result.status}")

        # Validate items
        validated_items = []
        for item in result.forecast_items:
            is_valid, errors = MeteorologicalValidator.validate_observation(item.model_dump())
            if is_valid:
                validated_items.append(item)
            else:
                logger.warning(f"Discarding physically anomalous GFS point: {errors}")

        result.forecast_items = validated_items
        return result
