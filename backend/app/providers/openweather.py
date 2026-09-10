import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.providers.base import WeatherProvider, ForecastProvider
from app.schemas.weather import (
    NormalizedWeatherResponse,
    LocationInfo,
    CurrentWeather,
    ForecastItem,
)
from app.schemas.forecast_common import CommonForecastItem, CommonModelForecastResponse
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OpenWeatherProvider(WeatherProvider, ForecastProvider):
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    GEO_URL = "https://api.openweathermap.org/geo/1.0"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENWEATHER_API_KEY

    @property
    def provider_name(self) -> str:
        return "OpenWeather"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_openweather_api_key_here")

    async def _resolve_coordinates(
        self, city: Optional[str], lat: Optional[float], lon: Optional[float]
    ) -> tuple[float, float, str, str]:
        if lat is not None and lon is not None:
            return lat, lon, city or f"Coord({lat:.2f}, {lon:.2f})", "IN"

        if not city:
            city = "Chennai"

        if not self.is_configured:
            raise ValueError("OpenWeather API key is not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{self.GEO_URL}/direct",
                params={"q": city, "limit": 1, "appid": self.api_key},
            )
            res.raise_for_status()
            data = res.json()
            if not data:
                raise ValueError(f"City '{city}' not found on OpenWeather")
            return data[0]["lat"], data[0]["lon"], data[0]["name"], data[0].get("country", "IN")

    async def get_current_weather(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> NormalizedWeatherResponse:
        if not self.is_configured:
            raise ValueError("OpenWeather provider is not configured. Set OPENWEATHER_API_KEY in .env.")

        resolved_lat, resolved_lon, resolved_name, country = await self._resolve_coordinates(city, lat, lon)

        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "lat": resolved_lat,
                "lon": resolved_lon,
                "units": "metric",
                "appid": self.api_key,
            }
            res = await client.get(f"{self.BASE_URL}/weather", params=params)
            res.raise_for_status()
            raw = res.json()

        sys_data = raw.get("sys", {})
        sunrise_ts = sys_data.get("sunrise")
        sunset_ts = sys_data.get("sunset")
        sunrise_str = datetime.fromtimestamp(sunrise_ts).strftime("%H:%M") if sunrise_ts else None
        sunset_str = datetime.fromtimestamp(sunset_ts).strftime("%H:%M") if sunset_ts else None

        current = CurrentWeather(
            temperature=float(raw["main"]["temp"]),
            feels_like=float(raw["main"]["feels_like"]),
            humidity=int(raw["main"]["humidity"]),
            wind_speed=float(raw["wind"]["speed"]),
            wind_deg=float(raw["wind"].get("deg", 0)),
            visibility=float(raw.get("visibility", 10000)),
            condition=raw["weather"][0]["description"].title(),
            condition_code=raw["weather"][0]["main"],
            pressure=float(raw["main"].get("pressure", 1013)),
            sunrise=sunrise_str,
            sunset=sunset_str,
        )

        return NormalizedWeatherResponse(
            location=LocationInfo(
                name=raw.get("name") or resolved_name,
                country=country,
                latitude=resolved_lat,
                longitude=resolved_lon,
            ),
            current=current,
            forecast=[],
            alerts=[],
            source="OpenWeather API",
            attribution_notes="Real-time meteorological observation via OpenWeather",
        )

    async def get_forecast(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
    ) -> NormalizedWeatherResponse:
        if not self.is_configured:
            raise ValueError("OpenWeather provider is not configured. Set OPENWEATHER_API_KEY in .env.")

        resolved_lat, resolved_lon, resolved_name, country = await self._resolve_coordinates(city, lat, lon)

        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "lat": resolved_lat,
                "lon": resolved_lon,
                "units": "metric",
                "appid": self.api_key,
            }
            # Current weather
            curr_res = await client.get(f"{self.BASE_URL}/weather", params=params)
            curr_res.raise_for_status()
            curr_raw = curr_res.json()

            # 5-day forecast
            fc_res = await client.get(f"{self.BASE_URL}/forecast", params=params)
            fc_res.raise_for_status()
            fc_raw = fc_res.json()

        sys_data = curr_raw.get("sys", {})
        sunrise_ts = sys_data.get("sunrise")
        sunset_ts = sys_data.get("sunset")
        sunrise_str = datetime.fromtimestamp(sunrise_ts).strftime("%H:%M") if sunrise_ts else None
        sunset_str = datetime.fromtimestamp(sunset_ts).strftime("%H:%M") if sunset_ts else None

        current = CurrentWeather(
            temperature=float(curr_raw["main"]["temp"]),
            feels_like=float(curr_raw["main"]["feels_like"]),
            humidity=int(curr_raw["main"]["humidity"]),
            wind_speed=float(curr_raw["wind"]["speed"]),
            wind_deg=float(curr_raw["wind"].get("deg", 0)),
            visibility=float(curr_raw.get("visibility", 10000)),
            condition=curr_raw["weather"][0]["description"].title(),
            condition_code=curr_raw["weather"][0]["main"],
            pressure=float(curr_raw["main"].get("pressure", 1013)),
            sunrise=sunrise_str,
            sunset=sunset_str,
        )

        forecast_items: List[ForecastItem] = []
        for item in fc_raw.get("list", []):
            rain_val = 0.0
            if "rain" in item and "3h" in item["rain"]:
                rain_val = float(item["rain"]["3h"])

            forecast_items.append(
                ForecastItem(
                    time=item["dt_txt"],
                    temperature=float(item["main"]["temp"]),
                    temperature_min=float(item["main"].get("temp_min")),
                    temperature_max=float(item["main"].get("temp_max")),
                    feels_like=float(item["main"].get("feels_like")),
                    humidity=int(item["main"]["humidity"]),
                    wind_speed=float(item["wind"]["speed"]),
                    wind_deg=float(item["wind"].get("deg", 0)),
                    condition=item["weather"][0]["description"].title(),
                    condition_code=item["weather"][0]["main"],
                    pop=float(item.get("pop", 0.0)),
                    rain_mm=rain_val,
                )
            )

        return NormalizedWeatherResponse(
            location=LocationInfo(
                name=curr_raw.get("name") or resolved_name,
                country=country,
                latitude=resolved_lat,
                longitude=resolved_lon,
            ),
            current=current,
            forecast=forecast_items,
            alerts=[],
            source="OpenWeather API",
            attribution_notes="Forecast model data via OpenWeather 5-Day/3-Hour Service",
        )

    async def get_common_forecast(
        self, lat: float, lon: float, days: int = 5
    ) -> CommonModelForecastResponse:
        """Normalizes OpenWeather forecast into CommonModelForecastResponse."""
        if not self.is_configured:
            return CommonModelForecastResponse(
                provider="openweather",
                model="OpenWeather Global NWP",
                source="OpenWeather Ltd.",
                available=False,
                configured=False,
                status="Provider not configured (Missing OPENWEATHER_API_KEY)",
                latitude=lat,
                longitude=lon,
                forecast_items=[],
                attribution_notes="Set OPENWEATHER_API_KEY in environment to enable OpenWeather.",
            )

        try:
            norm = await self.get_forecast(lat=lat, lon=lon, days=days)
            items: List[CommonForecastItem] = []
            for it in norm.forecast:
                avail = ["temperature", "humidity", "wind_speed", "condition"]
                if it.feels_like is not None:
                    avail.append("feels_like")
                if it.rain_mm is not None:
                    avail.append("precipitation")
                if it.pop is not None:
                    avail.append("precipitation_probability")

                items.append(
                    CommonForecastItem(
                        provider="openweather",
                        model="OpenWeather Global NWP",
                        source=norm.source,
                        run_time="Latest",
                        forecast_time=it.time,
                        latitude=lat,
                        longitude=lon,
                        temperature=it.temperature,
                        feels_like=it.feels_like,
                        humidity=it.humidity,
                        precipitation=it.rain_mm,
                        precipitation_probability=it.pop,
                        wind_speed=it.wind_speed,
                        wind_direction=it.wind_deg,
                        condition=it.condition,
                        available_variables=avail,
                    )
                )

            return CommonModelForecastResponse(
                provider="openweather",
                model="OpenWeather Global NWP",
                source="OpenWeather 2.5 API",
                available=True,
                configured=True,
                status="Available / Operational",
                resolution="~10 km",
                run_time="Latest 3-Hour Cycle",
                latitude=lat,
                longitude=lon,
                forecast_items=items,
                attribution_notes="OpenWeather meteorological observation & forecast.",
            )
        except Exception as ex:
            logger.warning(f"OpenWeather common forecast failed: {ex}")
            return CommonModelForecastResponse(
                provider="openweather",
                model="OpenWeather Global NWP",
                source="OpenWeather 2.5 API",
                available=False,
                configured=True,
                status=f"OpenWeather unavailable ({str(ex)})",
                latitude=lat,
                longitude=lon,
                forecast_items=[],
                attribution_notes="Upstream OpenWeather request error.",
            )
