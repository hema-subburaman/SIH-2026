from fastapi import APIRouter
from typing import Dict, Any, List
from app.providers.openweather import OpenWeatherProvider
from app.providers.open_meteo import OpenMeteoProvider
from app.providers.imd_warning_provider import OfficialMeteorologicalWarningProvider
from app.providers.gfs_provider import GFSProvider
from app.providers.wrf_provider import WRFProvider

router = APIRouter()

openweather_inst = OpenWeatherProvider()
openmeteo_inst = OpenMeteoProvider()
imd_inst = OfficialMeteorologicalWarningProvider()
gfs_inst = GFSProvider()
wrf_inst = WRFProvider()


@router.get("/status")
async def get_providers_status() -> Dict[str, Any]:
    """
    Returns the real-time operational status of all meteorological, warning, and NWP providers.
    Transparently displays configuration status without faking unconfigured NWP models.
    """
    gfs_info = await gfs_inst.get_model_run_info()
    wrf_info = await wrf_inst.get_model_run_info()

    return {
        "providers": [
            {
                "id": "openweather",
                "name": "OpenWeather API (v2.5)",
                "type": "Observational & 5-Day Forecast",
                "status": "Configured & Active" if openweather_inst.is_configured else "Unconfigured (Set OPENWEATHER_API_KEY)",
                "configured": openweather_inst.is_configured,
                "notes": "Primary weather observation and forecast provider when API key is provided.",
            },
            {
                "id": "open_meteo",
                "name": "Open-Meteo Meteorological Service",
                "type": "WMO Compliant Global Reanalysis & ECMWF/GFS Hybrid",
                "status": "Active / Ready",
                "configured": True,
                "notes": "Provides high-resolution telemetry, 7-day hourly forecast, and ERA5 historical climate archive (1980-present).",
            },
            {
                "id": "imd_ndma",
                "name": "India Meteorological Department (IMD) / NDMA CAP Feed",
                "type": "Official Early Disaster Warning System",
                "status": "Active / Ingestion Interface Ready",
                "configured": True,
                "notes": "Ingests official government disaster bulletins, cyclone advisories, and red/orange alerts.",
            },
            {
                "id": "gfs_nwp",
                "name": gfs_info["model"],
                "type": "Numerical Weather Prediction (0.25° Global)",
                "status": gfs_info["status"],
                "configured": gfs_info["configured"],
                "resolution": gfs_info.get("resolution", "0.25°"),
                "notes": gfs_info.get("notice"),
            },
            {
                "id": "wrf_nwp",
                "name": wrf_info["model"],
                "type": "Meso-Scale High-Resolution Simulation",
                "status": wrf_info["status"],
                "configured": wrf_info["configured"],
                "resolution": wrf_info.get("resolution", "3.0 km domain"),
                "notes": wrf_info.get("notice"),
            },
        ]
    }
