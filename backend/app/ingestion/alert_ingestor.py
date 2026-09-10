from typing import Any, Dict, Optional, List
from app.ingestion.base_ingestor import BaseIngestor
from app.providers.imd_warning_provider import OfficialMeteorologicalWarningProvider
from app.schemas.alert import AlertItem
import logging

logger = logging.getLogger(__name__)


class AlertIngestor(BaseIngestor):
    """Worker for ingesting official disaster early warnings (IMD/NDMA)."""

    def __init__(self):
        super().__init__(
            name="IMD_Official_Alert_Ingestor",
            provider="imd_ndma",
            timeout_seconds=12.0,
            max_retries=2,
            backoff_factor=1.5,
        )
        self.provider_instance = OfficialMeteorologicalWarningProvider()

    async def fetch_and_parse(self, city: str = "Chennai", lat: Optional[float] = None, lon: Optional[float] = None, **kwargs) -> List[AlertItem]:
        alerts = await self.provider_instance.get_alerts(city=city, lat=lat, lon=lon)
        return alerts
