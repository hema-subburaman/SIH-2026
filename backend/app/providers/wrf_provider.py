from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
import math
import logging
import httpx
from app.providers.base import NWPProvider
from app.schemas.forecast_common import CommonForecastItem, CommonModelForecastResponse

logger = logging.getLogger(__name__)

try:
    import xarray as xr
except ImportError:
    xr = None


class WRFProvider(NWPProvider):
    """
    Weather Research and Forecasting (WRF-ARW) Meso-Scale Model Provider.
    Ingests high-resolution localized numerical simulation datasets (1 km - 4 km domain) from:
    1. Local WRF NetCDF simulation outputs (wrfout_d01_*, wrfout_d02_*) via WRF_NETCDF_PATH
    2. High-performance WRF simulation cluster REST endpoint via WRF_MODEL_ENDPOINT

    CRITICAL: Strict zero-fabrication policy. If WRF data is not configured or offline,
    returns a structured unconfigured/unavailable state. Never fabricates numerical model outputs.
    """

    def __init__(self):
        self.endpoint = os.getenv("WRF_MODEL_ENDPOINT", "").strip()
        self.nc_path = os.getenv("WRF_NETCDF_PATH", "").strip()

    @property
    def model_name(self) -> str:
        return "Weather Research and Forecasting (WRF-ARW Meso-scale)"

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint or (self.nc_path and os.path.exists(self.nc_path)))

    async def get_model_run_info(self) -> Dict[str, Any]:
        """Returns operational metadata for the WRF meso-scale model."""
        if not self.is_configured:
            return {
                "model": self.model_name,
                "provider": "wrf",
                "status": "Provider not configured",
                "configured": False,
                "available": False,
                "source": "NCAR / Meso-scale WRF Ingest Pipeline",
                "resolution": "3.0 km nested meso-scale domain",
                "notice": "WRF NetCDF pipeline ready for HPC integration. Configure WRF_MODEL_ENDPOINT or WRF_NETCDF_PATH.",
                "capabilities": [
                    "High-Res Urban Microclimate",
                    "Localized Cloudburst & Flash Flood Prediction",
                    "Coastal Sea-Breeze Infiltration",
                    "Orographic Wind Acceleration",
                ],
                "last_updated": None,
            }

        return {
            "model": self.model_name,
            "provider": "wrf",
            "status": "Available / Active" if (self.endpoint or os.path.exists(self.nc_path)) else "Configured",
            "configured": True,
            "available": True,
            "source": "Local WRF-ARW Simulation Run",
            "resolution": "3.0 km domain",
            "endpoint": self.endpoint or self.nc_path,
            "capabilities": [
                "2m Temperature (T2)",
                "Accumulated Precipitation (RAINC + RAINNC)",
                "Surface Wind Vectors (U10 / V10)",
                "Surface Pressure (PSFC)",
                "2m Water Vapor Mixing Ratio (Q2)",
            ],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def get_grid_forecast(
        self, lat: float, lon: float, step_hours: int = 1
    ) -> Dict[str, Any]:
        """Raw grid forecast extraction for NWPProvider ABC."""
        common = await self.get_common_forecast(lat=lat, lon=lon, days=3)
        return {
            "model": self.model_name,
            "provider": "wrf",
            "lat": lat,
            "lon": lon,
            "configured": common.configured,
            "available": common.available,
            "status": common.status,
            "forecast_count": len(common.forecast_items),
            "forecasts": [item.model_dump() for item in common.forecast_items],
        }

    async def get_common_forecast(
        self, lat: float, lon: float, days: int = 3
    ) -> CommonModelForecastResponse:
        """
        Extracts and normalizes WRF NetCDF simulation data for the requested coordinates.
        Returns structured unavailable state if unconfigured or unreadable. Zero synthetic data.
        """
        # If not configured: return unconfigured state immediately
        if not self.is_configured:
            return CommonModelForecastResponse(
                provider="wrf",
                model=self.model_name,
                source="WRF-ARW Meso-scale",
                available=False,
                configured=False,
                status="WRF data source not configured",
                resolution="3.0 km domain",
                latitude=lat,
                longitude=lon,
                forecast_items=[],
                attribution_notes="WRF meso-scale model cluster is not configured in environment.",
            )

        # Path 1: Local NetCDF file or directory
        if self.nc_path and os.path.exists(self.nc_path) and xr is not None:
            try:
                # Open NetCDF dataset (handles single wrfout file or multifile)
                ds = xr.open_dataset(self.nc_path)
                # WRF coordinates are typically XLAT and XLONG 2D arrays
                if "XLAT" in ds and "XLONG" in ds:
                    xlat = ds["XLAT"].values
                    xlong = ds["XLONG"].values
                    # If 3D (time, south_north, west_east), take first time slice for coordinates
                    if xlat.ndim == 3:
                        xlat = xlat[0]
                        xlong = xlong[0]

                    # Euclidean distance to find nearest grid cell
                    dist = (xlat - lat) ** 2 + (xlong - lon) ** 2
                    sn_idx, we_idx = divmod(dist.argmin(), dist.shape[1])

                    items: List[CommonForecastItem] = []
                    times = ds["Times"].values if "Times" in ds else range(min(days * 24, 72))

                    for step_i in range(len(times)):
                        t_val = times[step_i]
                        if isinstance(t_val, bytes):
                            t_str = t_val.decode("utf-8").replace("_", "T")
                        else:
                            t_str = str(t_val)

                        # T2 in Kelvin -> Celsius
                        temp_c = None
                        if "T2" in ds:
                            raw_t = float(ds["T2"].values[step_i, sn_idx, we_idx])
                            temp_c = round(raw_t - 273.15, 1)

                        # Precipitation = RAINC + RAINNC (accumulated mm)
                        precip_mm = None
                        if "RAINC" in ds and "RAINNC" in ds:
                            p_c = float(ds["RAINC"].values[step_i, sn_idx, we_idx])
                            p_nc = float(ds["RAINNC"].values[step_i, sn_idx, we_idx])
                            precip_mm = round(p_c + p_nc, 1)

                        # Wind components U10, V10
                        wind_spd = None
                        wind_dir = None
                        if "U10" in ds and "V10" in ds:
                            u = float(ds["U10"].values[step_i, sn_idx, we_idx])
                            v = float(ds["V10"].values[step_i, sn_idx, we_idx])
                            wind_spd = round(math.sqrt(u**2 + v**2), 1)
                            # Meteorological wind direction (direction wind blows from)
                            deg = (math.atan2(-u, -v) * 180 / math.pi) % 360
                            wind_dir = round(deg, 1)

                        # Surface pressure PSFC (Pa -> hPa)
                        pressure_hpa = None
                        if "PSFC" in ds:
                            pressure_hpa = round(float(ds["PSFC"].values[step_i, sn_idx, we_idx]) / 100.0, 1)

                        avail = [k for k, v in [
                            ("temperature", temp_c),
                            ("precipitation", precip_mm),
                            ("wind_speed", wind_spd),
                            ("wind_direction", wind_dir),
                            ("pressure", pressure_hpa),
                        ] if v is not None]

                        items.append(
                            CommonForecastItem(
                                provider="wrf",
                                model=self.model_name,
                                source="Local WRF NetCDF",
                                forecast_time=t_str,
                                latitude=lat,
                                longitude=lon,
                                temperature=temp_c,
                                feels_like=temp_c,
                                precipitation=precip_mm,
                                wind_speed=wind_spd,
                                wind_direction=wind_dir,
                                pressure=pressure_hpa,
                                condition="WRF Simulation",
                                available_variables=avail,
                            )
                        )

                    return CommonModelForecastResponse(
                        provider="wrf",
                        model=self.model_name,
                        source="WRF-ARW Meso-scale Simulation",
                        available=True,
                        configured=True,
                        status="Active / Ingested",
                        resolution="3.0 km domain",
                        latitude=lat,
                        longitude=lon,
                        forecast_items=items,
                        attribution_notes="WRF-ARW high-resolution meso-scale grid simulation.",
                    )
            except Exception as ex:
                logger.error(f"Failed to read WRF NetCDF from {self.nc_path}: {ex}")

        # Path 2: Dedicated WRF REST Cluster Endpoint
        if self.endpoint:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{self.endpoint.rstrip('/')}/forecast",
                        params={"lat": lat, "lon": lon, "days": days},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_items = data.get("forecasts", [])
                        items = [CommonForecastItem(**item) for item in raw_items]
                        return CommonModelForecastResponse(
                            provider="wrf",
                            model=self.model_name,
                            source="WRF-ARW HPC Cluster",
                            available=True,
                            configured=True,
                            status="Active / Cluster Connected",
                            resolution="3.0 km domain",
                            latitude=lat,
                            longitude=lon,
                            forecast_items=items,
                            attribution_notes="WRF meso-scale simulation from high-performance computing node.",
                        )
                    else:
                        logger.warning(f"WRF cluster returned HTTP {resp.status_code}")
            except Exception as ex:
                logger.warning(f"Failed to reach WRF cluster at {self.endpoint}: {ex}")

        # If configured but unavailable:
        return CommonModelForecastResponse(
            provider="wrf",
            model=self.model_name,
            source="WRF-ARW Meso-scale",
            available=False,
            configured=True,
            status="WRF data source unavailable (cluster offline or NetCDF unreadable)",
            resolution="3.0 km domain",
            latitude=lat,
            longitude=lon,
            forecast_items=[],
            attribution_notes="WRF simulation service is currently unreachable.",
        )
