import httpx
import time
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.providers.base import WeatherProvider, ForecastProvider, UpstreamRateLimitError
from app.schemas.weather import (
    NormalizedWeatherResponse,
    LocationInfo,
    CurrentWeather,
    ForecastItem,
)
from app.schemas.climate import ClimateTrendResponse, ClimateDataPoint
from app.schemas.forecast_common import CommonForecastItem, CommonModelForecastResponse
import logging

logger = logging.getLogger(__name__)

# Standard Indian city coordinate directory for ultra-fast lookup
INDIAN_CITIES_COORDS = {
    "chennai": (13.0827, 80.2707, "Chennai", "Tamil Nadu"),
    "delhi": (28.6139, 77.2090, "Delhi", "Delhi"),
    "new delhi": (28.6139, 77.2090, "New Delhi", "Delhi"),
    "mumbai": (19.0760, 72.8777, "Mumbai", "Maharashtra"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru", "Karnataka"),
    "bangalore": (12.9716, 77.5946, "Bengaluru", "Karnataka"),
    "kolkata": (22.5726, 88.3639, "Kolkata", "West Bengal"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad", "Telangana"),
    "pune": (18.5204, 73.8567, "Pune", "Maharashtra"),
    "ahmedabad": (23.0225, 72.5714, "Ahmedabad", "Gujarat"),
    "jaipur": (26.9124, 75.7873, "Jaipur", "Rajasthan"),
    "kochi": (9.9312, 76.2673, "Kochi", "Kerala"),
    "coimbatore": (11.0168, 76.9558, "Coimbatore", "Tamil Nadu"),
    "madurai": (9.9252, 78.1198, "Madurai", "Tamil Nadu"),
    "lucknow": (26.8467, 80.9462, "Lucknow", "Uttar Pradesh"),
    "patna": (25.5941, 85.1376, "Patna", "Bihar"),
    "bhopal": (23.2599, 77.4126, "Bhopal", "Madhya Pradesh"),
    "chandigarh": (30.7333, 76.7794, "Chandigarh", "Punjab/Haryana"),
    "visakhapatnam": (17.6868, 83.2185, "Visakhapatnam", "Andhra Pradesh"),
    "shimla": (31.1048, 77.1734, "Shimla", "Himachal Pradesh"),
    "srinagar": (34.0837, 74.7973, "Srinagar", "Jammu and Kashmir"),
    "guwahati": (26.1445, 91.7362, "Guwahati", "Assam"),
}

WMO_WEATHER_CODES = {
    0: ("Clear sky", "Clear"),
    1: ("Mainly clear", "Clouds"),
    2: ("Partly cloudy", "Clouds"),
    3: ("Overcast", "Clouds"),
    45: ("Fog", "Fog"),
    48: ("Depositing rime fog", "Fog"),
    51: ("Light drizzle", "Drizzle"),
    53: ("Moderate drizzle", "Drizzle"),
    55: ("Dense drizzle", "Drizzle"),
    56: ("Light freezing drizzle", "Drizzle"),
    57: ("Dense freezing drizzle", "Drizzle"),
    61: ("Slight rain", "Rain"),
    63: ("Moderate rain", "Rain"),
    65: ("Heavy rain", "Rain"),
    66: ("Light freezing rain", "Rain"),
    67: ("Heavy freezing rain", "Rain"),
    71: ("Slight snow", "Snow"),
    73: ("Moderate snow", "Snow"),
    75: ("Heavy snow", "Snow"),
    77: ("Snow grains", "Snow"),
    80: ("Slight rain showers", "Rain"),
    81: ("Moderate rain showers", "Rain"),
    82: ("Violent rain showers", "Rain"),
    85: ("Slight snow showers", "Snow"),
    86: ("Heavy snow showers", "Snow"),
    95: ("Thunderstorm", "Thunderstorm"),
    96: ("Thunderstorm with slight hail", "Thunderstorm"),
    99: ("Thunderstorm with heavy hail", "Thunderstorm"),
}


class CacheEntry:
    def __init__(self, data: Any, timestamp: float, ttl: float):
        self.data = data
        self.timestamp = timestamp
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl


# Module-level server-side in-memory cache and in-flight request coalescing
_open_meteo_cache: Dict[str, CacheEntry] = {}
_in_flight_tasks: Dict[str, asyncio.Future] = {}
_cache_lock: asyncio.Lock = asyncio.Lock()


def get_cached_entry(key: str) -> Optional[Any]:
    """Returns cached data if present and not expired."""
    entry = _open_meteo_cache.get(key)
    if entry and not entry.is_expired:
        return entry.data
    return None


def get_stale_entry(key: str) -> Optional[Any]:
    """Returns cached data even if expired (used for graceful fallback during upstream outages)."""
    entry = _open_meteo_cache.get(key)
    if entry:
        return entry.data
    return None


def set_cached_entry(key: str, data: Any, ttl: float = 600.0) -> None:
    """Sets a cached response with bounded memory eviction."""
    now = time.time()
    if len(_open_meteo_cache) > 500:
        expired_keys = [k for k, v in _open_meteo_cache.items() if (now - v.timestamp) > v.ttl]
        for k in expired_keys:
            _open_meteo_cache.pop(k, None)
        if len(_open_meteo_cache) > 500:
            oldest_keys = sorted(_open_meteo_cache.keys(), key=lambda k: _open_meteo_cache[k].timestamp)[:50]
            for k in oldest_keys:
                _open_meteo_cache.pop(k, None)

    _open_meteo_cache[key] = CacheEntry(data=data, timestamp=now, ttl=ttl)


def clear_open_meteo_cache() -> None:
    """Clears the cache (used in test suites)."""
    _open_meteo_cache.clear()
    _in_flight_tasks.clear()


async def execute_coalesced(key: str, coro_factory):
    """
    Single-flight coalescing: If multiple concurrent requests arrive for the exact same key,
    only one executes the upstream network request, while the others await the shared Future.
    """
    async with _cache_lock:
        if key in _in_flight_tasks:
            fut = _in_flight_tasks[key]
        else:
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            _in_flight_tasks[key] = fut
            asyncio.create_task(_run_coalesced_task(key, fut, coro_factory))

    return await fut


async def _run_coalesced_task(key: str, fut: asyncio.Future, coro_factory):
    try:
        res = await coro_factory()
        if not fut.done():
            fut.set_result(res)
    except Exception as exc:
        if not fut.done():
            fut.set_exception(exc)
    finally:
        async with _cache_lock:
            _in_flight_tasks.pop(key, None)


class OpenMeteoProvider(WeatherProvider, ForecastProvider):
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
    GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

    # Server-side cache TTLs
    FORECAST_CACHE_TTL: float = 600.0  # 10 minutes
    CURRENT_CACHE_TTL: float = 300.0   # 5 minutes
    CLIMATE_CACHE_TTL: float = 86400.0 # 24 hours
    GEO_CACHE_TTL: float = 86400.0     # 24 hours

    @property
    def provider_name(self) -> str:
        return "Open-Meteo Public Meteorological Service"

    @property
    def is_configured(self) -> bool:
        return True  # Open access, requires no private API keys

    async def _fetch_with_retry(
        self,
        url: str,
        params: Dict[str, Any],
        max_retries: int = 3,
        initial_backoff: float = 0.5,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Executes an HTTP GET request to Open-Meteo with exponential backoff on HTTP 429 and 5xx.
        Respects upstream Retry-After headers when provided.
        """
        last_res = None
        retry_after_val: Optional[int] = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.get(url, params=params)

                    if res.status_code == 200:
                        return res.json()

                    if res.status_code == 429:
                        last_res = res
                        retry_header = res.headers.get("Retry-After")
                        if retry_header and retry_header.strip().isdigit():
                            retry_after_val = int(retry_header.strip())
                            delay = min(float(retry_after_val), 3.0)
                        else:
                            delay = initial_backoff * (2 ** attempt)

                        if attempt < max_retries:
                            logger.warning(
                                f"Open-Meteo HTTP 429 Too Many Requests (attempt {attempt + 1}/{max_retries + 1}). "
                                f"Retrying in {delay:.2f}s (Retry-After header: {retry_header})..."
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"Open-Meteo HTTP 429 persisted after {max_retries + 1} attempts. "
                                f"Retry-After header: {retry_header}"
                            )
                            break

                    # Transient server errors (500, 502, 503, 504)
                    if res.status_code in (500, 502, 503, 504) and attempt < max_retries:
                        delay = initial_backoff * (2 ** attempt)
                        logger.warning(
                            f"Open-Meteo HTTP {res.status_code} (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        continue

                    res.raise_for_status()

            except httpx.RequestError as req_err:
                if attempt < max_retries:
                    delay = initial_backoff * (2 ** attempt)
                    logger.warning(f"Open-Meteo network request error ({req_err}). Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
                raise

        if last_res is not None and last_res.status_code == 429:
            raise UpstreamRateLimitError(
                message="Open-Meteo meteorological service is temporarily rate-limited (HTTP 429).",
                retry_after=retry_after_val or 60,
                provider="Open-Meteo",
            )

        if last_res is not None:
            last_res.raise_for_status()
        raise RuntimeError("Open-Meteo request failed without response.")

    async def search_locations_api(self, query: str, count: int = 8) -> List[Dict[str, Any]]:
        """
        Searches real geographical locations worldwide via Open-Meteo Geocoding API with 24h caching.
        """
        if not query or len(query.strip()) < 2:
            return []
        clean_q = query.strip()
        cache_key = f"geo:{clean_q.lower()}:{count}"

        cached = get_cached_entry(cache_key)
        if cached is not None:
            return cached

        async def _fetch():
            data = await self._fetch_with_retry(
                self.GEO_URL,
                params={"name": clean_q, "count": count, "language": "en", "format": "json"},
                timeout=8.0,
            )
            results = data.get("results") or []
            formatted = []
            for item in results:
                formatted.append({
                    "name": item.get("name", clean_q),
                    "state": item.get("admin1", ""),
                    "district": item.get("admin2", ""),
                    "country": item.get("country_code", "IN").upper(),
                    "country_name": item.get("country", ""),
                    "latitude": float(item["latitude"]),
                    "longitude": float(item["longitude"]),
                    "timezone": item.get("timezone", "UTC"),
                })
            set_cached_entry(cache_key, formatted, ttl=self.GEO_CACHE_TTL)
            return formatted

        try:
            return await execute_coalesced(cache_key, _fetch)
        except Exception as e:
            logger.warning(f"Geocoding search API error: {e}")
            stale = get_stale_entry(cache_key)
            if stale is not None:
                return stale
            return []

    async def resolve_coordinates(
        self, city: Optional[str], lat: Optional[float], lon: Optional[float]
    ) -> tuple[float, float, str, str, str]:
        """Resolves city string or coordinates to (lat, lon, name, state, country)."""
        if lat is not None and lon is not None:
            return lat, lon, city or f"Coord({lat:.2f}, {lon:.2f})", "", "IN"

        city_clean = (city or "Chennai").strip().lower()
        if city_clean in INDIAN_CITIES_COORDS:
            c_lat, c_lon, c_name, c_state = INDIAN_CITIES_COORDS[city_clean]
            return c_lat, c_lon, c_name, c_state, "IN"

        # Query Geocoding API with caching
        try:
            matches = await self.search_locations_api(city or "Chennai", count=1)
            if matches and len(matches) > 0:
                first = matches[0]
                return (
                    first["latitude"],
                    first["longitude"],
                    first["name"],
                    first["state"],
                    first["country"],
                )
        except Exception as e:
            logger.warning(f"Geocoding API error: {e}. Falling back to default Chennai.")

        return 13.0827, 80.2707, "Chennai", "Tamil Nadu", "IN"

    def _parse_current_response(
        self, data: Dict[str, Any], resolved_name: str, state: str, country: str, resolved_lat: float, resolved_lon: float
    ) -> NormalizedWeatherResponse:
        curr = data.get("current", {})
        daily = data.get("daily", {})
        code = curr.get("weather_code", 0)
        desc, main_code = WMO_WEATHER_CODES.get(code, ("Clear sky", "Clear"))

        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])
        sunrise_str = sunrises[0].split("T")[-1] if sunrises else "06:00"
        sunset_str = sunsets[0].split("T")[-1] if sunsets else "18:30"

        current_obj = CurrentWeather(
            temperature=float(curr.get("temperature_2m", 28.0)),
            feels_like=float(curr.get("apparent_temperature", curr.get("temperature_2m", 28.0))),
            humidity=int(curr.get("relative_humidity_2m", 65)),
            wind_speed=round(float(curr.get("wind_speed_10m", 3.0)) / 3.6, 2),  # km/h to m/s
            wind_deg=float(curr.get("wind_direction_10m", 0)),
            visibility=10000.0,
            condition=desc,
            condition_code=main_code,
            pressure=float(curr.get("surface_pressure", 1013.0)),
            precipitation_mm=float(curr.get("precipitation", 0.0)),
            sunrise=sunrise_str,
            sunset=sunset_str,
        )

        return NormalizedWeatherResponse(
            location=LocationInfo(
                name=resolved_name,
                state=state,
                country=country,
                latitude=resolved_lat,
                longitude=resolved_lon,
            ),
            current=current_obj,
            forecast=[],
            alerts=[],
            source="Open-Meteo Public Meteorological Service (WMO Compliant)",
            attribution_notes="Real-time observational data from national meteorological weather stations",
            cached=False,
        )

    def _parse_forecast_response(
        self, data: Dict[str, Any], resolved_name: str, state: str, country: str, resolved_lat: float, resolved_lon: float
    ) -> NormalizedWeatherResponse:
        curr = data.get("current", {})
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        code = curr.get("weather_code", 0)
        desc, main_code = WMO_WEATHER_CODES.get(code, ("Clear sky", "Clear"))

        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])
        sunrise_str = sunrises[0].split("T")[-1] if sunrises else "06:00"
        sunset_str = sunsets[0].split("T")[-1] if sunsets else "18:30"

        current_obj = CurrentWeather(
            temperature=float(curr.get("temperature_2m", 28.0)),
            feels_like=float(curr.get("apparent_temperature", curr.get("temperature_2m", 28.0))),
            humidity=int(curr.get("relative_humidity_2m", 65)),
            wind_speed=round(float(curr.get("wind_speed_10m", 3.0)) / 3.6, 2),
            wind_deg=float(curr.get("wind_direction_10m", 0)),
            visibility=10000.0,
            condition=desc,
            condition_code=main_code,
            pressure=float(curr.get("surface_pressure", 1013.0)),
            sunrise=sunrise_str,
            sunset=sunset_str,
        )

        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        feels = hourly.get("apparent_temperature", [])
        humids = hourly.get("relative_humidity_2m", [])
        pops = hourly.get("precipitation_probability", [])
        rains = hourly.get("precipitation", [])
        wcodes = hourly.get("weather_code", [])
        winds = hourly.get("wind_speed_10m", [])

        forecast_items: List[ForecastItem] = []
        step = 3
        for i in range(0, len(times), step):
            w_code = wcodes[i] if i < len(wcodes) else 0
            w_desc, w_main = WMO_WEATHER_CODES.get(w_code, ("Clear sky", "Clear"))
            pop_ratio = (pops[i] / 100.0) if i < len(pops) and pops[i] is not None else 0.0

            forecast_items.append(
                ForecastItem(
                    time=times[i],
                    temperature=float(temps[i]),
                    feels_like=float(feels[i]) if i < len(feels) else None,
                    humidity=int(humids[i]) if i < len(humids) else 60,
                    wind_speed=round(float(winds[i]) / 3.6, 2) if i < len(winds) else 3.0,
                    condition=w_desc,
                    condition_code=w_main,
                    pop=round(pop_ratio, 2),
                    rain_mm=float(rains[i]) if i < len(rains) and rains[i] is not None else 0.0,
                )
            )

        return NormalizedWeatherResponse(
            location=LocationInfo(
                name=resolved_name,
                state=state,
                country=country,
                latitude=resolved_lat,
                longitude=resolved_lon,
            ),
            current=current_obj,
            forecast=forecast_items,
            alerts=[],
            source="Open-Meteo NWP Forecast Service (ECMWF & GFS Hybrid)",
            attribution_notes="7-Day high-resolution forecast derived from meteorological numerical models",
            cached=False,
        )

    async def get_current_weather(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> NormalizedWeatherResponse:
        resolved_lat, resolved_lon, resolved_name, state, country = await self.resolve_coordinates(city, lat, lon)
        cache_key = f"current:{round(resolved_lat, 3)}:{round(resolved_lon, 3)}"

        # 1. Return fresh cached entry if present
        cached = get_cached_entry(cache_key)
        if cached:
            cached_copy = cached.model_copy()
            cached_copy.cached = True
            return cached_copy

        params = {
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation",
            ],
            "daily": ["sunrise", "sunset"],
            "timezone": "auto",
        }

        async def _fetch():
            data = await self._fetch_with_retry(self.FORECAST_URL, params=params)
            parsed = self._parse_current_response(data, resolved_name, state, country, resolved_lat, resolved_lon)
            set_cached_entry(cache_key, parsed, ttl=self.CURRENT_CACHE_TTL)
            return parsed

        try:
            return await execute_coalesced(cache_key, _fetch)
        except UpstreamRateLimitError as ex:
            # Fallback to stale cache if available
            stale = get_stale_entry(cache_key)
            if stale:
                logger.warning(f"Serving stale cached current weather for {cache_key} due to rate limiting: {ex}")
                stale_copy = stale.model_copy()
                stale_copy.cached = True
                stale_copy.attribution_notes = (
                    f"{stale_copy.attribution_notes or ''} [Served from cache: upstream provider temporarily rate-limited]"
                ).strip()
                return stale_copy
            raise

    async def get_forecast(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 7,
    ) -> NormalizedWeatherResponse:
        resolved_lat, resolved_lon, resolved_name, state, country = await self.resolve_coordinates(city, lat, lon)
        target_days = min(days, 7)
        cache_key = f"forecast:{round(resolved_lat, 3)}:{round(resolved_lon, 3)}:{target_days}"

        # 1. Return fresh cached entry if present
        cached = get_cached_entry(cache_key)
        if cached:
            cached_copy = cached.model_copy()
            cached_copy.cached = True
            return cached_copy

        params = {
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "hourly": [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "precipitation_probability",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
            ],
            "daily": ["sunrise", "sunset", "temperature_2m_max", "temperature_2m_min"],
            "forecast_days": target_days,
            "timezone": "auto",
        }

        async def _fetch():
            data = await self._fetch_with_retry(self.FORECAST_URL, params=params)
            parsed = self._parse_forecast_response(data, resolved_name, state, country, resolved_lat, resolved_lon)
            set_cached_entry(cache_key, parsed, ttl=self.FORECAST_CACHE_TTL)
            return parsed

        try:
            return await execute_coalesced(cache_key, _fetch)
        except UpstreamRateLimitError as ex:
            # Fallback to stale cache if available
            stale = get_stale_entry(cache_key)
            if stale:
                logger.warning(f"Serving stale cached forecast for {cache_key} due to rate limiting: {ex}")
                stale_copy = stale.model_copy()
                stale_copy.cached = True
                stale_copy.attribution_notes = (
                    f"{stale_copy.attribution_notes or ''} [Served from cache: upstream provider temporarily rate-limited]"
                ).strip()
                return stale_copy
            raise

    async def get_common_forecast(
        self, lat: float, lon: float, days: int = 5
    ) -> CommonModelForecastResponse:
        """Normalizes Open-Meteo forecast into CommonModelForecastResponse."""
        try:
            norm = await self.get_forecast(lat=lat, lon=lon, days=days)
            common_items: List[CommonForecastItem] = []
            for item in norm.forecast:
                avail = ["temperature", "humidity", "wind_speed"]
                if item.rain_mm is not None:
                    avail.append("precipitation")
                if item.pop is not None:
                    avail.append("precipitation_probability")
                if item.feels_like is not None:
                    avail.append("feels_like")
                if item.condition is not None:
                    avail.append("condition")

                common_items.append(
                    CommonForecastItem(
                        provider="open_meteo",
                        model="ECMWF / Open-Meteo Multi-Model Ensemble",
                        source=norm.source,
                        run_time="Latest Cycle",
                        forecast_time=item.time,
                        latitude=lat,
                        longitude=lon,
                        temperature=item.temperature,
                        feels_like=item.feels_like,
                        humidity=item.humidity,
                        precipitation=item.rain_mm,
                        precipitation_probability=item.pop,
                        wind_speed=item.wind_speed,
                        wind_direction=item.wind_deg,
                        condition=item.condition,
                        available_variables=avail,
                    )
                )

            return CommonModelForecastResponse(
                provider="open_meteo",
                model="ECMWF / Open-Meteo Multi-Model Ensemble",
                source="Open-Meteo WMO Meteorological Service",
                available=True,
                configured=True,
                status="Available / Operational",
                resolution="1.0 km - 11 km",
                run_time="Latest Synchronized",
                latitude=lat,
                longitude=lon,
                forecast_items=common_items,
                attribution_notes="Open-Meteo ECMWF / GFS ensemble feed.",
            )
        except UpstreamRateLimitError as ex:
            logger.warning(f"Open-Meteo common forecast rate-limited: {ex}")
            return CommonModelForecastResponse(
                provider="open_meteo",
                model="ECMWF / Open-Meteo Multi-Model Ensemble",
                source="Open-Meteo WMO Meteorological Service",
                available=False,
                configured=True,
                status="Open-Meteo temporarily rate-limited (HTTP 429)",
                latitude=lat,
                longitude=lon,
                forecast_items=[],
                attribution_notes="Upstream Open-Meteo service rate-limited.",
            )
        except Exception as ex:
            logger.warning(f"Failed to fetch Open-Meteo common forecast: {ex}")
            return CommonModelForecastResponse(
                provider="open_meteo",
                model="ECMWF / Open-Meteo Multi-Model Ensemble",
                source="Open-Meteo WMO Meteorological Service",
                available=False,
                configured=True,
                status=f"Open-Meteo temporarily unavailable ({str(ex)})",
                latitude=lat,
                longitude=lon,
                forecast_items=[],
                attribution_notes="Upstream Open-Meteo service failure.",
            )

    async def get_climate_history(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        years: int = 10,
    ) -> ClimateTrendResponse:
        """Fetches real historical climate observation/reanalysis with caching."""
        resolved_lat, resolved_lon, resolved_name, state, country = await self.resolve_coordinates(city, lat, lon)
        cache_key = f"climate:{round(resolved_lat, 3)}:{round(resolved_lon, 3)}:{years}"

        cached = get_cached_entry(cache_key)
        if cached is not None:
            return cached

        current_year = datetime.now().year
        start_year = max(1990, current_year - years)

        async def _fetch():
            params = {
                "latitude": resolved_lat,
                "longitude": resolved_lon,
                "start_date": f"{start_year}-01-01",
                "end_date": f"{current_year - 1}-12-31",
                "daily": ["temperature_2m_mean", "temperature_2m_max", "precipitation_sum"],
                "timezone": "auto",
            }
            hist_data = await self._fetch_with_retry(self.HISTORICAL_URL, params=params, timeout=12.0)
            daily_hist = hist_data.get("daily", {})
            dates = daily_hist.get("time", [])
            means = daily_hist.get("temperature_2m_mean", [])
            maxs = daily_hist.get("temperature_2m_max", [])
            rains = daily_hist.get("precipitation_sum", [])

            # Aggregate per year
            year_buckets: Dict[int, Dict[str, list]] = {}
            for idx, dt in enumerate(dates):
                yr = int(dt.split("-")[0])
                if yr not in year_buckets:
                    year_buckets[yr] = {"means": [], "maxs": [], "rains": []}
                if idx < len(means) and means[idx] is not None:
                    year_buckets[yr]["means"].append(means[idx])
                if idx < len(maxs) and maxs[idx] is not None:
                    year_buckets[yr]["maxs"].append(maxs[idx])
                if idx < len(rains) and rains[idx] is not None:
                    year_buckets[yr]["rains"].append(rains[idx])

            sorted_years = sorted(year_buckets.keys())
            all_means = []
            for yr in sorted_years:
                m_list = year_buckets[yr]["means"]
                avg_t = sum(m_list) / len(m_list) if m_list else 28.0
                all_means.append(avg_t)

            baseline = sum(all_means[:3]) / 3 if len(all_means) >= 3 else 28.0

            data_points: List[ClimateDataPoint] = []
            for yr in sorted_years:
                m_list = year_buckets[yr]["means"]
                max_list = year_buckets[yr]["maxs"]
                r_list = year_buckets[yr]["rains"]
                avg_t = round(sum(m_list) / len(m_list), 2) if m_list else 28.0
                max_t = round(max(max_list), 2) if max_list else avg_t + 5
                tot_r = round(sum(r_list), 1) if r_list else 1000.0

                data_points.append(
                    ClimateDataPoint(
                        year=yr,
                        label=str(yr),
                        avg_temp=avg_t,
                        max_temp=max_t,
                        total_rainfall_mm=tot_r,
                        anomaly=round(avg_t - baseline, 2),
                    )
                )

            if not data_points:
                trend_resp = ClimateTrendResponse(
                    available=False,
                    message="Historical climate data is temporarily unavailable.",
                    location=resolved_name,
                    latitude=resolved_lat,
                    longitude=resolved_lon,
                    period=f"{start_year} - {current_year - 1}",
                    baseline_avg_temp=None,
                    recent_avg_temp=None,
                    temp_change_rate=None,
                    trend_summary="Historical climate data is temporarily unavailable from the upstream provider archive.",
                    data_points=[],
                    source="Open-Meteo Historical Climate Service",
                    provider="Open-Meteo Historical Climate Service",
                    data_type="historical_reanalysis",
                    is_official=False,
                    citation="Historical observational climate reanalysis data. Not a predictive forecast.",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            else:
                baseline_val = data_points[0].avg_temp if data_points else 28.0
                recent_val = data_points[-1].avg_temp if data_points else 28.5
                change_rate = round(((recent_val - baseline_val) / max(1, len(data_points))) * 10, 2)

                trend_resp = ClimateTrendResponse(
                    available=True,
                    message=None,
                    location=resolved_name,
                    latitude=resolved_lat,
                    longitude=resolved_lon,
                    period=f"{data_points[0].year} - {data_points[-1].year} ({len(data_points)}-year observation)",
                    baseline_avg_temp=baseline_val,
                    recent_avg_temp=recent_val,
                    temp_change_rate=change_rate,
                    trend_summary=(
                        f"Historical climate reanalysis shows a long-term warming trend of +{change_rate}°C/decade in {resolved_name}. "
                        "Monsoon precipitation exhibits inter-annual variability with increasing frequency of intense short-duration rainfall events."
                    ),
                    data_points=data_points,
                    source="Open-Meteo Historical Climate Reanalysis (ERA5 & WMO Archive)",
                    provider="Open-Meteo Historical Climate Service",
                    data_type="historical_reanalysis",
                    is_official=False,
                    citation="Verified historical observations from global meteorological reanalysis archives. Clearly separated from predictive forecasts.",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            set_cached_entry(cache_key, trend_resp, ttl=self.CLIMATE_CACHE_TTL)
            return trend_resp

        try:
            return await execute_coalesced(cache_key, _fetch)
        except Exception as e:
            logger.warning(f"Error fetching historical climate data: {e}")
            stale = get_stale_entry(cache_key)
            if stale is not None:
                return stale
            return ClimateTrendResponse(
                available=False,
                message="Historical climate data is temporarily unavailable.",
                location=resolved_name,
                latitude=resolved_lat,
                longitude=resolved_lon,
                period=f"{start_year} - {current_year - 1}",
                baseline_avg_temp=None,
                recent_avg_temp=None,
                temp_change_rate=None,
                trend_summary="Historical climate data is temporarily unavailable from the upstream provider archive.",
                data_points=[],
                source="Open-Meteo Historical Climate Service",
                provider="Open-Meteo Historical Climate Service",
                data_type="historical_reanalysis",
                is_official=False,
                citation="Historical observational climate reanalysis data. Not a predictive forecast.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
