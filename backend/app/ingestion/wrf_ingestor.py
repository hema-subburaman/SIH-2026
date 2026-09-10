from typing import Any, Dict, Optional, List
from app.ingestion.base_ingestor import BaseIngestor
from app.providers.wrf_provider import WRFProvider
from app.ingestion.validator import MeteorologicalValidator
from app.schemas.forecast_common import CommonModelForecastResponse
import logging

logger = logging.getLogger(__name__)


class WRFIngestor(BaseIngestor):
    """Worker for WRF-ARW meso-scale simulation dataset ingestion."""

    def __init__(self):
        super().__init__(
            name="WRF_MesoScale_Ingestor",
            provider="wrf",
            timeout_seconds=15.0,
            max_retries=1,
            backoff_factor=2.0,
        )
        self.provider_instance = WRFProvider()

    async def fetch_and_parse(self, lat: float = 13.0827, lon: float = 80.2707, days: int = 3, **kwargs) -> CommonModelForecastResponse:
        result = await self.provider_instance.get_common_forecast(lat=lat, lon=lon, days=days)
        if not result.available:
            raise RuntimeError(f"WRF Ingestion: {result.status}")

        validated_items = []
        for item in result.forecast_items:
            is_valid, errors = MeteorologicalValidator.validate_observation(item.model_dump())
            if is_valid:
                validated_items.append(item)
            else:
                logger.warning(f"Discarding physically anomalous WRF point: {errors}")

        result.forecast_items = validated_items
        return result
