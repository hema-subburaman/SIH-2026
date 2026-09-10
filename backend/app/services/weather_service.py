from typing import Optional, List, Dict, Any
from app.schemas.weather import NormalizedWeatherResponse
from app.providers.openweather import OpenWeatherProvider
from app.providers.open_meteo import OpenMeteoProvider, INDIAN_CITIES_COORDS
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Central Meteorological Orchestration Service.
    Coordinates between OpenWeather, Open-Meteo, and future NWP feeds.
    Provides transparent data normalization and source attribution.
    """

    def __init__(self):
        self.openweather = OpenWeatherProvider()
        self.open_meteo = OpenMeteoProvider()

    async def get_current_weather(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        preferred_provider: Optional[str] = None
    ) -> NormalizedWeatherResponse:
        # 1. Try OpenWeather if configured and requested
        if (preferred_provider == "openweather" or not preferred_provider) and self.openweather.is_configured:
            try:
                res = await self.openweather.get_current_weather(city=city, lat=lat, lon=lon)
                return res
            except Exception as e:
                logger.warning(f"OpenWeather current request failed: {e}. Falling back to Open-Meteo.")

        # 2. Open-Meteo fallback (Real-time meteorological observations)
        return await self.open_meteo.get_current_weather(city=city, lat=lat, lon=lon)

    async def get_forecast(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
        preferred_provider: Optional[str] = None
    ) -> NormalizedWeatherResponse:
        if (preferred_provider == "openweather" or not preferred_provider) and self.openweather.is_configured:
            try:
                res = await self.openweather.get_forecast(city=city, lat=lat, lon=lon, days=days)
                return res
            except Exception as e:
                logger.warning(f"OpenWeather forecast request failed: {e}. Falling back to Open-Meteo.")

        return await self.open_meteo.get_forecast(city=city, lat=lat, lon=lon, days=days)

    async def search_locations(self, query: str) -> List[Dict[str, Any]]:
        """Fast location autocomplete / resolver for Indian cities and global coordinates."""
        q = query.strip().lower()
        results: List[Dict[str, Any]] = []

        # Check local Indian directory first
        for key, val in INDIAN_CITIES_COORDS.items():
            if q in key or key in q:
                results.append({
                    "name": val[2],
                    "state": val[3],
                    "country": "IN",
                    "latitude": val[0],
                    "longitude": val[1]
                })

        # Also resolve via Geocoding API if query is outside dictionary
        if len(results) < 3 and len(q) >= 2:
            try:
                lat, lon, name, state, country = await self.open_meteo.resolve_coordinates(city=query, lat=None, lon=None)
                if not any(r["name"].lower() == name.lower() for r in results):
                    results.append({
                        "name": name,
                        "state": state,
                        "country": country,
                        "latitude": lat,
                        "longitude": lon
                    })
            except Exception:
                pass

        return results


weather_service = WeatherService()
