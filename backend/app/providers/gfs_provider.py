from typing import Dict, Any, Optional
from app.providers.base import NWPProvider
import os


class GFSProvider(NWPProvider):
    """
    NOAA Global Forecast System (GFS) Model Provider.
    Designed for ingesting 0.25-degree GRIB2 datasets from NOMADS / AWS Open Data.
    """

    def __init__(self):
        # Checks if custom GFS endpoint or GRIB2 processing bucket is configured
        self.endpoint = os.getenv("GFS_NWP_ENDPOINT", "")
        self.s3_bucket = os.getenv("GFS_S3_BUCKET", "")

    @property
    def model_name(self) -> str:
        return "NOAA Global Forecast System (GFS 0.25°)"

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.endpoint.strip())

    async def get_model_run_info(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "model": self.model_name,
                "status": "Provider not configured",
                "configured": False,
                "resolution": "0.25 degree (~28 km horizontal grid)",
                "cycles": ["00Z", "06Z", "12Z", "18Z"],
                "notice": "Integration interface ready. Configure GFS_NWP_ENDPOINT or NOMADS ingest pipeline in environment.",
                "capabilities": ["Wind Shear", "Convective Available Potential Energy (CAPE)", "Total Precipitable Water"],
            }

        return {
            "model": self.model_name,
            "status": "Active / Configured",
            "configured": True,
            "endpoint": self.endpoint,
            "latest_run": "00Z Cycle",
        }

    async def get_grid_forecast(
        self, lat: float, lon: float, step_hours: int = 3
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise NotImplementedError(
                "GFS NWP Provider is not configured with a local NOMADS GRIB2 ingest server. Status: Provider not configured."
            )
        return {
            "model": self.model_name,
            "lat": lat,
            "lon": lon,
            "configured": True,
        }
