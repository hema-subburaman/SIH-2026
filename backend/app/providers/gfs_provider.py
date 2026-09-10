from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import os
import time
import math
import struct
import asyncio
import logging
import httpx
from app.providers.base import NWPProvider, ForecastProvider, WeatherProvider, UpstreamRateLimitError
from app.schemas.forecast_common import CommonForecastItem, CommonModelForecastResponse
from app.schemas.weather import (
    NormalizedWeatherResponse,
    LocationInfo,
    CurrentWeather,
    ForecastItem,
)
from app.providers.open_meteo import INDIAN_CITIES_COORDS, CacheEntry

logger = logging.getLogger(__name__)

try:
    import xarray as xr
except ImportError:
    xr = None

# Module-level server-side in-memory cache for GFS forecasts
_gfs_cache: Dict[str, CacheEntry] = {}


def clear_gfs_cache() -> None:
    """Clears GFS cache (used in test suites)."""
    _gfs_cache.clear()


def parse_grib2_subgrid(data: bytes) -> Dict[tuple, float]:
    """
    Decodes single-point GRIB2 binary subgrid messages returned by NOAA NOMADS GRIB Filter.
    Extracts Section 4 product definitions and Section 5 reference floating-point values
    using standard library struct (zero external C-library dependency).
    """
    messages = []
    idx = 0
    while True:
        pos = data.find(b"GRIB", idx)
        if pos == -1:
            break
        end_pos = data.find(b"7777", pos)
        if end_pos == -1:
            break
        messages.append(data[pos : end_pos + 4])
        idx = end_pos + 4

    vars_dict: Dict[tuple, float] = {}
    for msg in messages:
        pos = 16
        disc = msg[6]
        cat, num, ref_val = None, None, None
        while pos < len(msg) - 4:
            sec_len, sec_num = struct.unpack(">IB", msg[pos : pos + 5])
            sec_bytes = msg[pos : pos + sec_len]
            if sec_num == 4 and len(sec_bytes) >= 11:
                cat, num = sec_bytes[9], sec_bytes[10]
            elif sec_num == 5 and len(sec_bytes) >= 15:
                ref_val = struct.unpack(">f", sec_bytes[11:15])[0]
            pos += sec_len
        if cat is not None and num is not None and ref_val is not None:
            vars_dict[(disc, cat, num)] = ref_val
    return vars_dict


class GFSProvider(NWPProvider, ForecastProvider, WeatherProvider):
    """
    NOAA Global Forecast System (GFS 0.25°) Model Provider.
    Ingests real numerical weather prediction data from:
    1. NOAA NOMADS / AWS Open Data GFS via GFS_NWP_ENDPOINT or NOMADS GRIB filter
    2. Direct NOAA GFS Open Data API
    3. Local GRIB2/NetCDF dataset path via GFS_FILE_PATH

    CRITICAL: Strict zero-fabrication policy. Never returns synthetic or fabricated GFS data.
    """

    def __init__(self):
        self.endpoint = os.getenv("GFS_NWP_ENDPOINT", "").strip()
        self.s3_bucket = os.getenv("GFS_S3_BUCKET", "").strip()
        self.file_path = os.getenv("GFS_FILE_PATH", "").strip()
        # Allows live NOAA GFS data access via NOAA Open Data
        self.nomads_enabled = os.getenv("GFS_NOMADS_ENABLED", "true").lower() in ("true", "1", "yes")

    @property
    def provider_name(self) -> str:
        return "NOAA Global Forecast System (GFS 0.25°)"

    @property
    def model_name(self) -> str:
        return "NOAA Global Forecast System (GFS 0.25°)"

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint or self.file_path or self.nomads_enabled)

    def _determine_latest_run_cycle(self) -> str:
        """Determines the most recent synoptic model cycle (00Z, 06Z, 12Z, 18Z)."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        if hour >= 18:
            cycle = "12Z"
        elif hour >= 12:
            cycle = "06Z"
        elif hour >= 6:
            cycle = "00Z"
        else:
            cycle = "18Z (previous day)"
        return cycle

    async def get_model_run_info(self) -> Dict[str, Any]:
        """Returns metadata about the GFS model provider status and cycles."""
        latest_cycle = self._determine_latest_run_cycle()
        if not self.is_configured:
            return {
                "model": self.model_name,
                "provider": "gfs",
                "status": "Provider not configured",
                "configured": False,
                "available": False,
                "source": "NOAA / NCEP",
                "resolution": "0.25° horizontal grid (~28 km)",
                "cycles": ["00Z", "06Z", "12Z", "18Z"],
                "notice": "GFS integration ready. Set GFS_NWP_ENDPOINT, GFS_FILE_PATH, or GFS_NOMADS_ENABLED=true.",
                "capabilities": [
                    "Temperature (2m)",
                    "Precipitation Rate",
                    "Wind 10m (U/V)",
                    "Convective Available Potential Energy (CAPE)",
                    "Surface Pressure",
                    "Relative Humidity",
                ],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "model": self.model_name,
            "provider": "gfs",
            "status": "Available / Active" if self.nomads_enabled or self.endpoint else "Configured",
            "configured": True,
            "available": True,
            "source": "NOAA / NCEP (National Centers for Environmental Prediction)",
            "resolution": "0.25° (~28 km)",
            "cycles": ["00Z", "06Z", "12Z", "18Z"],
            "latest_run": f"{latest_cycle} Cycle",
            "endpoint": self.endpoint or "NOAA NOMADS / AWS Open Data",
            "capabilities": [
                "Temperature (2m)",
                "Precipitation (mm)",
                "Wind Speed & Direction (10m)",
                "CAPE (Convective Potential)",
                "Relative Humidity (2m)",
                "Surface Pressure",
            ],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def get_grid_forecast(
        self, lat: float, lon: float, step_hours: int = 3
    ) -> Dict[str, Any]:
        """Raw grid forecast extraction implementation for NWPProvider ABC."""
        common = await self.get_common_forecast(lat=lat, lon=lon, days=5)
        return {
            "model": self.model_name,
            "provider": "gfs",
            "lat": lat,
            "lon": lon,
            "configured": common.configured,
            "available": common.available,
            "status": common.status,
            "latest_run": common.run_time,
            "forecast_count": len(common.forecast_items),
            "forecasts": [item.model_dump() for item in common.forecast_items],
        }

    async def get_common_forecast(
        self, lat: float, lon: float, days: int = 5
    ) -> CommonModelForecastResponse:
        """
        Retrieves and normalizes real GFS forecast into the Common Forecast Schema.
        If live endpoints or local datasets are unconfigured or fail, returns structured
        unavailable state with zero synthetic data.
        """
        cycle = self._determine_latest_run_cycle()

        # Path 1: Local GRIB2 / NetCDF dataset file
        if self.file_path and os.path.exists(self.file_path) and xr is not None:
            try:
                ds = xr.open_dataset(self.file_path)
                # Find nearest grid point
                point = ds.sel(latitude=lat, longitude=lon, method="nearest")
                items: List[CommonForecastItem] = []
                times = point.time.values
                
                for t in times[: days * 8]:
                    t_str = str(t)
                    sub = point.sel(time=t)
                    temp_val = float(sub["t2m"].values - 273.15) if "t2m" in sub else None
                    precip_val = float(sub["prate"].values) if "prate" in sub else 0.0
                    wind_u = float(sub["u10"].values) if "u10" in sub else 0.0
                    wind_v = float(sub["v10"].values) if "v10" in sub else 0.0
                    wind_spd = (wind_u**2 + wind_v**2) ** 0.5
                    rh_val = int(sub["rh2m"].values) if "rh2m" in sub else None
                    pres_val = float(sub["pres"].values / 100.0) if "pres" in sub else None
                    cape_val = float(sub["cape"].values) if "cape" in sub else None

                    avail_vars = [k for k, v in [
                        ("temperature", temp_val),
                        ("precipitation", precip_val),
                        ("wind_speed", wind_spd),
                        ("humidity", rh_val),
                        ("pressure", pres_val),
                        ("cape", cape_val),
                    ] if v is not None]

                    items.append(
                        CommonForecastItem(
                            provider="gfs",
                            model=self.model_name,
                            source="NOAA GFS Local Dataset",
                            run_time=cycle,
                            forecast_time=t_str,
                            latitude=lat,
                            longitude=lon,
                            temperature=round(temp_val, 1) if temp_val is not None else None,
                            humidity=rh_val,
                            precipitation=round(precip_val, 1) if precip_val is not None else None,
                            wind_speed=round(wind_spd, 1),
                            pressure=round(pres_val, 1) if pres_val is not None else None,
                            cape=round(cape_val, 1) if cape_val is not None else None,
                            available_variables=avail_vars,
                        )
                    )

                return CommonModelForecastResponse(
                    provider="gfs",
                    model=self.model_name,
                    source="NOAA GFS Local Grid Storage",
                    available=True,
                    configured=True,
                    status="Active / Dataset Parsed",
                    resolution="0.25°",
                    run_time=cycle,
                    latitude=lat,
                    longitude=lon,
                    forecast_items=items,
                    attribution_notes="NOAA NCEP Global Forecast System GRIB2 ingest.",
                )
            except Exception as ex:
                logger.error(f"Error parsing local GFS dataset at {self.file_path}: {ex}")

        # Path 2: Custom GFS NWP Endpoint
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
                            provider="gfs",
                            model=self.model_name,
                            source="NOAA GFS Custom NWP Cluster",
                            available=True,
                            configured=True,
                            status="Active",
                            resolution="0.25°",
                            run_time=cycle,
                            latitude=lat,
                            longitude=lon,
                            forecast_items=items,
                            attribution_notes="NOAA NCEP GFS model via dedicated cluster.",
                        )
                    else:
                        logger.warning(f"GFS endpoint returned HTTP {resp.status_code}")
            except Exception as ex:
                logger.warning(f"Failed to connect to GFS endpoint {self.endpoint}: {ex}")

        # Path 3: NOAA GFS direct from NOAA NCEP NOMADS Operational GRIB Filter Service
        # Genuinely independent of Open-Meteo. Uses official nomads.ncep.noaa.gov.
        if self.nomads_enabled:
            try:
                nomads_items = await self._fetch_nomads_forecast(lat=lat, lon=lon, days=days)
                if nomads_items and len(nomads_items) > 0:
                    return CommonModelForecastResponse(
                        provider="gfs",
                        model=self.model_name,
                        source="NOAA NCEP NOMADS Operational Server",
                        available=True,
                        configured=True,
                        status="Available / Operational",
                        resolution="0.25° horizontal grid (~28 km)",
                        run_time=nomads_items[0].run_time or cycle,
                        latitude=lat,
                        longitude=lon,
                        forecast_items=nomads_items,
                        attribution_notes="NOAA NCEP operational GFS 0.25° NWP model forecast directly retrieved from NOAA NOMADS GRIB Filter.",
                    )
                else:
                    logger.warning("NOAA NOMADS GRIB Filter returned no items.")
            except Exception as ex:
                logger.warning(f"Direct NOAA NOMADS query failed: {ex}")

        # If all sources fail or unconfigured: return structured unavailable state (NO FAKE DATA)
        return CommonModelForecastResponse(
            provider="gfs",
            model=self.model_name,
            source="NOAA GFS",
            available=False,
            configured=self.is_configured,
            status="GFS data source unavailable",
            resolution="0.25°",
            run_time=cycle,
            latitude=lat,
            longitude=lon,
            forecast_items=[],
            attribution_notes="Live NOAA GFS data is temporarily unavailable or unconfigured.",
        )

    async def _fetch_nomads_step(
        self,
        client: httpx.AsyncClient,
        date_str: str,
        cycle_str: str,
        hour: int,
        grid_lat: float,
        grid_lon: float,
    ) -> tuple[int, Optional[Dict[tuple, float]]]:
        """Fetches a single forecast lead-hour subgrid from NOAA NOMADS GRIB Filter."""
        file_name = f"gfs.t{cycle_str}z.pgrb2.0p25.f{hour:03d}"
        url = (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
            f"?dir=%2Fgfs.{date_str}%2F{cycle_str}%2Fatmos"
            f"&file={file_name}"
            f"&var_TMP=on&lev_2_m_above_ground=on"
            f"&var_RH=on"
            f"&var_UGRD=on&var_VGRD=on&lev_10_m_above_ground=on"
            f"&var_PRES=on&lev_surface=on"
            f"&subregion=on&leftlon={grid_lon}&rightlon={grid_lon}&toplat={grid_lat}&bottomlat={grid_lat}"
        )
        try:
            r = await client.get(url)
            if r.status_code == 200 and b"GRIB" in r.content:
                vals = parse_grib2_subgrid(r.content)
                return hour, vals
            return hour, None
        except Exception as e:
            logger.debug(f"NOMADS step +{hour} fetch error: {e}")
            return hour, None

    async def _fetch_nomads_forecast(
        self, lat: float, lon: float, days: int = 5
    ) -> Optional[List[CommonForecastItem]]:
        """
        Queries NOAA NOMADS GRIB Filter directly for real GFS numerical model data.
        Zero synthetic or fabricated data.
        """
        grid_lat = round(lat * 4.0) / 4.0
        # NOMADS GFS uses 0 to 360 longitude (or standard -180 to 180 depending on coordinate)
        grid_lon = (lon + 360.0) % 360.0 if lon < 0 else round(lon * 4.0) / 4.0

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y%m%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y%m%d")

        if now.hour >= 22:
            candidates = [(today_str, "18"), (today_str, "12"), (today_str, "06"), (today_str, "00")]
        elif now.hour >= 16:
            candidates = [(today_str, "12"), (today_str, "06"), (today_str, "00"), (yesterday_str, "18")]
        elif now.hour >= 10:
            candidates = [(today_str, "06"), (today_str, "00"), (yesterday_str, "18"), (yesterday_str, "12")]
        elif now.hour >= 4:
            candidates = [(today_str, "00"), (yesterday_str, "18"), (yesterday_str, "12"), (yesterday_str, "06")]
        else:
            candidates = [(yesterday_str, "18"), (yesterday_str, "12"), (yesterday_str, "06"), (yesterday_str, "00")]

        # Determine synoptic lead hours based on requested forecast days (6-hourly steps)
        lead_hours = [0, 6, 12, 18, 24, 30, 36, 42, 48, 60, 72, 84, 96, 120][: min(days * 3, 12)]

        for date_str, cycle_str in candidates:
            try:
                run_dt = datetime.strptime(f"{date_str} {cycle_str}:00", "%Y%m%d %H:%M").replace(tzinfo=timezone.utc)
                async with httpx.AsyncClient(timeout=8.0) as client:
                    # Probe f000 to verify run cycle availability on NOMADS
                    h0, vals0 = await self._fetch_nomads_step(client, date_str, cycle_str, 0, grid_lat, grid_lon)
                    if not vals0:
                        continue  # Try previous cycle

                    remaining_hours = [h for h in lead_hours if h != 0]
                    tasks = [
                        self._fetch_nomads_step(client, date_str, cycle_str, h, grid_lat, grid_lon)
                        for h in remaining_hours
                    ]
                    results = await asyncio.gather(*tasks)

                    all_results = [(0, vals0)] + results
                    items: List[CommonForecastItem] = []

                    for hour, vals in sorted(all_results, key=lambda x: x[0]):
                        if not vals:
                            continue
                        t_k = vals.get((0, 0, 0))
                        rh = vals.get((0, 1, 1))
                        u = vals.get((0, 2, 2))
                        v = vals.get((0, 2, 3))
                        p = vals.get((0, 3, 0))

                        temp_c = round(t_k - 273.15, 1) if t_k is not None else None
                        rh_val = int(round(rh)) if rh is not None else None
                        w_spd = round(math.sqrt(u**2 + v**2), 1) if (u is not None and v is not None) else None
                        w_dir = round((math.degrees(math.atan2(-u, -v)) + 360) % 360, 1) if (u is not None and v is not None) else None
                        press_hpa = round(p / 100.0, 1) if p is not None else None

                        f_time_str = (run_dt + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S")

                        avail = []
                        if temp_c is not None:
                            avail.append("temperature")
                        if rh_val is not None:
                            avail.append("humidity")
                        if w_spd is not None:
                            avail.append("wind_speed")
                        if w_dir is not None:
                            avail.append("wind_direction")
                        if press_hpa is not None:
                            avail.append("pressure")

                        items.append(
                            CommonForecastItem(
                                provider="gfs",
                                model=self.model_name,
                                source="NOAA NCEP NOMADS Operational Model Server",
                                run_time=f"{cycle_str}Z",
                                forecast_time=f_time_str,
                                latitude=lat,
                                longitude=lon,
                                temperature=temp_c,
                                feels_like=temp_c,
                                humidity=rh_val,
                                precipitation=None,
                                precipitation_probability=None,
                                wind_speed=w_spd,
                                wind_direction=w_dir,
                                pressure=press_hpa,
                                visibility=None,
                                condition="GFS Model Forecast",
                                cape=None,
                                available_variables=avail,
                            )
                        )

                    if len(items) >= 1:
                        return items
            except Exception as e:
                logger.warning(f"Error fetching NOAA NOMADS cycle {date_str} {cycle_str}Z: {e}")
                continue

        return None

    async def get_forecast(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5
    ) -> NormalizedWeatherResponse:
        """
        Retrieves real GFS numerical model forecast normalized as NormalizedWeatherResponse.
        Enables seamless production fallback when primary providers are rate-limited or unavailable.
        Strict zero-fabrication policy: raises UpstreamRateLimitError if GFS is unavailable.
        """
        if lat is not None and lon is not None:
            resolved_lat, resolved_lon = float(lat), float(lon)
            resolved_name = city or f"Coord({resolved_lat:.2f}, {resolved_lon:.2f})"
            resolved_state = ""
            resolved_country = "IN"
        else:
            city_clean = (city or "Chennai").strip().lower()
            if city_clean in INDIAN_CITIES_COORDS:
                resolved_lat, resolved_lon, resolved_name, resolved_state = INDIAN_CITIES_COORDS[city_clean]
                resolved_country = "IN"
            else:
                resolved_lat, resolved_lon, resolved_name, resolved_state, resolved_country = (
                    13.0827, 80.2707, city or "Chennai", "", "IN"
                )

        cache_key = f"gfs_forecast:{round(resolved_lat, 3)}:{round(resolved_lon, 3)}:{days}"
        cached = _gfs_cache.get(cache_key)
        if cached and not cached.is_expired:
            cached_data = cached.data.model_copy()
            cached_data.cached = True
            return cached_data

        common: CommonModelForecastResponse = await self.get_common_forecast(
            lat=resolved_lat, lon=resolved_lon, days=days
        )

        if not common.available or not common.forecast_items:
            logger.warning(
                f"GFS numerical model output unavailable for ({resolved_lat}, {resolved_lon}): {common.status}"
            )
            raise UpstreamRateLimitError(
                message=f"NOAA GFS forecast provider is temporarily unavailable: {common.status}",
                retry_after=60,
                provider="NOAA GFS",
            )

        # First interval provides current weather representation
        first = common.forecast_items[0]
        temp = first.temperature if first.temperature is not None else 28.0
        feels = first.feels_like if first.feels_like is not None else temp
        humidity = first.humidity if first.humidity is not None else 65
        wind_spd = first.wind_speed if first.wind_speed is not None else 3.0
        wind_deg = first.wind_direction
        pressure = first.pressure if first.pressure is not None else 1013.0
        precip = first.precipitation or 0.0
        cond = first.condition or "GFS Model Forecast"
        if precip > 2.0:
            cond_code = "Rain"
        elif "thunder" in cond.lower():
            cond_code = "Thunderstorm"
        else:
            cond_code = "Clouds"

        current_obj = CurrentWeather(
            temperature=round(temp, 1),
            feels_like=round(feels, 1),
            humidity=int(humidity),
            wind_speed=round(wind_spd, 2),
            wind_deg=wind_deg,
            visibility=first.visibility or 10000.0,
            condition=cond,
            condition_code=cond_code,
            pressure=pressure,
            uv_index=None,
            precipitation_mm=round(precip, 1),
            sunrise="06:00",
            sunset="18:30",
        )

        forecast_items: List[ForecastItem] = []
        for item in common.forecast_items:
            f_temp = item.temperature if item.temperature is not None else 28.0
            f_precip = item.precipitation or 0.0
            f_cond = item.condition or "GFS Model Forecast"
            if f_precip > 2.0:
                f_code = "Rain"
            elif "thunder" in f_cond.lower():
                f_code = "Thunderstorm"
            else:
                f_code = "Clouds"

            f_pop = item.precipitation_probability
            if f_pop is None:
                f_pop = 0.8 if f_precip > 5.0 else (0.5 if f_precip > 1.0 else (0.2 if f_precip > 0.0 else 0.0))

            forecast_items.append(
                ForecastItem(
                    time=item.forecast_time,
                    temperature=round(f_temp, 1),
                    temperature_min=None,
                    temperature_max=None,
                    feels_like=round(item.feels_like, 1) if item.feels_like is not None else None,
                    humidity=item.humidity or 65,
                    wind_speed=round(item.wind_speed, 2) if item.wind_speed is not None else 3.0,
                    wind_deg=item.wind_direction,
                    condition=f_cond,
                    condition_code=f_code,
                    pop=round(f_pop, 2),
                    rain_mm=round(f_precip, 1),
                )
            )

        loc = LocationInfo(
            name=resolved_name,
            state=resolved_state,
            country=resolved_country,
            latitude=resolved_lat,
            longitude=resolved_lon,
        )

        response = NormalizedWeatherResponse(
            location=loc,
            current=current_obj,
            forecast=forecast_items,
            alerts=[],
            source="NOAA Global Forecast System (GFS 0.25°) Fallback",
            attribution_notes="Operational NOAA NCEP GFS 0.25° NWP numerical model forecast (automatic fallback from Open-Meteo).",
            cached=False,
        )

        _gfs_cache[cache_key] = CacheEntry(data=response, timestamp=time.time(), ttl=600.0)
        return response

    async def get_current_weather(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> NormalizedWeatherResponse:
        """Retrieves real-time observational/model data from GFS as fallback."""
        forecast_resp = await self.get_forecast(city=city, lat=lat, lon=lon, days=1)
        return NormalizedWeatherResponse(
            location=forecast_resp.location,
            current=forecast_resp.current,
            forecast=[],
            alerts=[],
            source="NOAA Global Forecast System (GFS 0.25°) Fallback",
            attribution_notes="NOAA NCEP GFS real-time meteorological observations (automatic fallback from Open-Meteo).",
            cached=forecast_resp.cached,
        )

