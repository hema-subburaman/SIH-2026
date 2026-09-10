from typing import Optional, List, Dict, Any
from app.schemas.weather import NormalizedWeatherResponse
from app.providers.openweather import OpenWeatherProvider
from app.providers.open_meteo import OpenMeteoProvider, INDIAN_CITIES_COORDS
from app.providers.gfs_provider import GFSProvider
from app.providers.base import UpstreamRateLimitError
import httpx
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Central Meteorological Orchestration Service.
    Coordinates between Open-Meteo (primary), NOAA GFS (automated production fallback),
    OpenWeather, and high-resolution WRF numerical prediction feeds.
    Provides transparent data normalization and honest source attribution.
    """

    def __init__(self):
        self.openweather = OpenWeatherProvider()
        self.open_meteo = OpenMeteoProvider()
        self.gfs = GFSProvider()

    async def get_current_weather(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        preferred_provider: Optional[str] = None
    ) -> NormalizedWeatherResponse:
        # 1. Try OpenWeather if explicitly preferred and configured
        if preferred_provider == "openweather" and self.openweather.is_configured:
            try:
                return await self.openweather.get_current_weather(city=city, lat=lat, lon=lon)
            except Exception as e:
                logger.warning(f"OpenWeather current request failed: {e}. Falling back to Open-Meteo.")

        # 2. Try GFS if explicitly preferred and configured
        if preferred_provider == "gfs" and self.gfs.is_configured:
            try:
                return await self.gfs.get_current_weather(city=city, lat=lat, lon=lon)
            except Exception as e:
                logger.warning(f"GFS direct current request failed: {e}. Falling back to Open-Meteo.")

        # 3. Primary provider: Open-Meteo
        try:
            return await self.open_meteo.get_current_weather(city=city, lat=lat, lon=lon)
        except (UpstreamRateLimitError, httpx.HTTPError, Exception) as om_err:
            logger.warning(
                f"Open-Meteo current observations failed ({type(om_err).__name__}: {om_err}). "
                f"Attempting automatic fallback to NOAA GFS..."
            )

            # 4. Fallback to GFS if available/configured
            if self.gfs.is_configured:
                try:
                    gfs_res = await self.gfs.get_current_weather(city=city, lat=lat, lon=lon)
                    if gfs_res and gfs_res.current:
                        logger.info(f"Successfully retrieved current observations from GFS fallback for {city or (lat, lon)}.")
                        return gfs_res
                except Exception as gfs_err:
                    logger.warning(f"GFS fallback for current weather failed ({type(gfs_err).__name__}: {gfs_err}).")

            # 5. Both Open-Meteo and GFS unavailable -> raise UpstreamRateLimitError for structured 503
            if isinstance(om_err, UpstreamRateLimitError):
                raise om_err
            raise UpstreamRateLimitError(
                message=f"Primary and fallback meteorological observation services are temporarily unavailable ({om_err}). Please retry shortly.",
                retry_after=60,
                provider="Open-Meteo / GFS",
            )

    async def get_forecast(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
        preferred_provider: Optional[str] = None
    ) -> NormalizedWeatherResponse:
        # 1. Try OpenWeather if explicitly preferred and configured
        if preferred_provider == "openweather" and self.openweather.is_configured:
            try:
                return await self.openweather.get_forecast(city=city, lat=lat, lon=lon, days=days)
            except Exception as e:
                logger.warning(f"OpenWeather forecast request failed: {e}. Falling back to Open-Meteo.")

        # 2. Try GFS if explicitly preferred and configured
        if preferred_provider == "gfs" and self.gfs.is_configured:
            try:
                res = await self.gfs.get_forecast(city=city, lat=lat, lon=lon, days=days)
                if res and res.forecast:
                    return res
            except Exception as e:
                logger.warning(f"GFS direct forecast request failed: {e}. Falling back to Open-Meteo.")

        # 3. Primary provider: Open-Meteo (with cache, backoff, and stale-while-error fallback)
        try:
            return await self.open_meteo.get_forecast(city=city, lat=lat, lon=lon, days=days)
        except (UpstreamRateLimitError, httpx.HTTPError, Exception) as om_err:
            logger.warning(
                f"Open-Meteo primary forecast provider failed ({type(om_err).__name__}: {om_err}). "
                f"Initiating automatic fallback to NOAA GFS..."
            )

            # 4. Fallback to GFS if available/configured
            if self.gfs.is_configured:
                try:
                    gfs_res = await self.gfs.get_forecast(city=city, lat=lat, lon=lon, days=days)
                    if gfs_res and gfs_res.forecast:
                        logger.info(f"Successfully retrieved forecast from NOAA GFS fallback for {city or (lat, lon)}.")
                        return gfs_res
                    else:
                        logger.warning("NOAA GFS fallback returned empty or unavailable forecast items.")
                except Exception as gfs_err:
                    logger.warning(f"NOAA GFS fallback failed ({type(gfs_err).__name__}: {gfs_err}).")

            # 5. Both Open-Meteo and GFS unavailable -> raise UpstreamRateLimitError for structured 503
            if isinstance(om_err, UpstreamRateLimitError):
                raise om_err
            raise UpstreamRateLimitError(
                message=f"Primary (Open-Meteo) and fallback (GFS) meteorological services are temporarily unavailable. Please retry shortly.",
                retry_after=60,
                provider="Open-Meteo / GFS",
            )

    async def search_locations(self, query: str) -> List[Dict[str, Any]]:
        """Search real locations worldwide (cities, towns, localities, villages, districts, states, countries)."""
        if not query or len(query.strip()) < 2:
            return []
        q = query.strip()

        # 1. Query live global geocoding API for real-time worldwide disambiguation
        api_results = await self.open_meteo.search_locations_api(q, count=8)
        if api_results:
            return api_results

        # 2. Fallback to local Indian city directory if offline or query matches
        fallback: List[Dict[str, Any]] = []
        q_lower = q.lower()
        for key, val in INDIAN_CITIES_COORDS.items():
            if q_lower in key or key in q_lower:
                fallback.append({
                    "name": val[2],
                    "state": val[3],
                    "district": "",
                    "country": "IN",
                    "country_name": "India",
                    "latitude": val[0],
                    "longitude": val[1],
                })
        return fallback


weather_service = WeatherService()
