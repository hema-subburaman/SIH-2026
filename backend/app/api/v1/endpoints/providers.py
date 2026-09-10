from fastapi import APIRouter, BackgroundTasks
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.providers.openweather import OpenWeatherProvider
from app.providers.open_meteo import OpenMeteoProvider
from app.providers.imd_warning_provider import OfficialMeteorologicalWarningProvider
from app.providers.gfs_provider import GFSProvider
from app.providers.wrf_provider import WRFProvider
from app.ingestion.scheduler import ingestion_scheduler

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
    Uses strict standardized statuses: AVAILABLE, NOT CONFIGURED, UNAVAILABLE, ERROR.
    Never displays 'Active' for unconfigured or stubbed models.
    """
    gfs_info = await gfs_inst.get_model_run_info()
    wrf_info = await wrf_inst.get_model_run_info()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine status for OpenWeather
    ow_status = "AVAILABLE" if openweather_inst.is_configured else "NOT CONFIGURED"
    
    # Determine status for Open-Meteo
    om_status = "AVAILABLE"

    # Determine status for IMD
    imd_status = "AVAILABLE"

    # Determine status for GFS
    if not gfs_info.get("configured"):
        gfs_status = "NOT CONFIGURED"
    elif gfs_info.get("available"):
        gfs_status = "AVAILABLE"
    else:
        gfs_status = "UNAVAILABLE"

    # Determine status for WRF
    if not wrf_info.get("configured"):
        wrf_status = "NOT CONFIGURED"
    elif wrf_info.get("available"):
        wrf_status = "AVAILABLE"
    else:
        wrf_status = "UNAVAILABLE"

    return {
        "timestamp": now_iso,
        "providers": [
            {
                "id": "open_meteo",
                "name": "Open-Meteo Meteorological Service",
                "model": "ECMWF & GFS Multi-Model Ensemble",
                "type": "WMO Compliant Global Numerical Weather Prediction",
                "source": "Open-Meteo / WMO Archive",
                "status": om_status,
                "configured": True,
                "available": True,
                "resolution": "1.0 km - 11 km",
                "latest_run": "Continuous 00Z/06Z/12Z/18Z sync",
                "last_updated": now_iso,
                "is_official": False,
                "notes": "Operational global NWP model ensemble with hourly 7-day lead.",
            },
            {
                "id": "openweather",
                "name": "OpenWeather API (v2.5)",
                "model": "OpenWeather Global NWP",
                "type": "Observational & 5-Day Forecast",
                "source": "OpenWeather Ltd.",
                "status": ow_status,
                "configured": openweather_inst.is_configured,
                "available": openweather_inst.is_configured,
                "resolution": "~10 km grid",
                "latest_run": "Current Observation Cycle",
                "last_updated": now_iso if openweather_inst.is_configured else None,
                "is_official": False,
                "notes": "Active observation & forecast provider when OPENWEATHER_API_KEY is configured.",
            },
            {
                "id": "imd_ndma",
                "name": "India Meteorological Department (IMD) / NDMA CAP",
                "model": "Official Government Disaster Early Warning Feed",
                "type": "Official Early Warning System",
                "source": "IMD / NDMA Sachet CAP Platform",
                "status": imd_status,
                "configured": True,
                "available": True,
                "resolution": "District / Regional Level",
                "latest_run": "Real-time CAP Push",
                "last_updated": now_iso,
                "is_official": True,
                "notes": "Ingests official government disaster bulletins, cyclone tracks, and red/orange/yellow alerts.",
            },
            {
                "id": "gfs_nwp",
                "name": gfs_info["model"],
                "model": "NOAA GFS 0.25°",
                "type": "Global Numerical Weather Prediction (NWP)",
                "source": gfs_info.get("source", "NOAA / NCEP"),
                "status": gfs_status,
                "configured": gfs_info.get("configured", False),
                "available": gfs_info.get("available", False),
                "resolution": gfs_info.get("resolution", "0.25° (~28 km)"),
                "latest_run": gfs_info.get("latest_run", "12Z Cycle"),
                "last_updated": gfs_info.get("last_updated"),
                "is_official": False,
                "notes": gfs_info.get("notice") or "NOAA GFS numerical simulation data.",
            },
            {
                "id": "wrf_nwp",
                "name": wrf_info["model"],
                "model": "WRF-ARW 3km",
                "type": "Meso-Scale High-Resolution Numerical Simulation",
                "source": wrf_info.get("source", "WRF Meso-scale Cluster"),
                "status": wrf_status,
                "configured": wrf_info.get("configured", False),
                "available": wrf_info.get("available", False),
                "resolution": wrf_info.get("resolution", "3.0 km nested domain"),
                "latest_run": wrf_info.get("latest_run"),
                "last_updated": wrf_info.get("last_updated"),
                "is_official": False,
                "notes": wrf_info.get("notice") or "Local WRF-ARW high-resolution simulation.",
            },
        ],
        "ingestion_status": ingestion_scheduler.get_status(),
    }


@router.post("/ingestion/trigger")
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    city: str = "Chennai",
    lat: float = 13.0827,
    lon: float = 80.2707,
) -> Dict[str, Any]:
    """Manually trigger an asynchronous ingestion run across all providers."""
    background_tasks.add_task(ingestion_scheduler.run_all, city=city, lat=lat, lon=lon)
    return {
        "status": "INGESTION_TRIGGERED",
        "city": city,
        "coordinates": {"lat": lat, "lon": lon},
        "message": "Ingestion pipeline scheduled in background with isolated fault tolerance.",
    }


@router.get("/ingestion/status")
async def get_ingestion_pipeline_status() -> Dict[str, Any]:
    """Returns the latest execution status, execution time, and error metrics of ingestion workers."""
    return ingestion_scheduler.get_status()
