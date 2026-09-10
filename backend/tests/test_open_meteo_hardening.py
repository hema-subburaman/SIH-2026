import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.providers.open_meteo import (
    OpenMeteoProvider,
    clear_open_meteo_cache,
    _open_meteo_cache,
    CacheEntry,
    get_cached_entry,
    set_cached_entry,
    execute_coalesced,
)
from app.providers.base import UpstreamRateLimitError
from app.schemas.weather import (
    NormalizedWeatherResponse,
    DetailedForecastResponse,
    LocationInfo,
    CurrentWeather,
)


MOCK_OPEN_METEO_PAYLOAD = {
    "latitude": 13.08,
    "longitude": 80.27,
    "current": {
        "time": "2026-09-10T12:00",
        "temperature_2m": 31.5,
        "relative_humidity_2m": 70,
        "apparent_temperature": 36.0,
        "precipitation": 0.0,
        "weather_code": 2,
        "wind_speed_10m": 14.2,
        "wind_direction_10m": 85,
        "surface_pressure": 1008.2,
    },
    "current_weather": {
        "temperature": 31.5,
        "windspeed": 14.2,
        "winddirection": 85,
        "weathercode": 2,
        "time": "2026-09-10T12:00",
    },
    "hourly": {
        "time": [
            "2026-09-10T12:00",
            "2026-09-10T15:00",
            "2026-09-10T18:00",
            "2026-09-10T21:00",
            "2026-09-11T00:00",
            "2026-09-11T03:00",
            "2026-09-11T06:00",
            "2026-09-11T09:00",
        ],
        "temperature_2m": [31.5, 30.2, 28.5, 27.0, 26.5, 26.0, 27.5, 30.0],
        "relativehumidity_2m": [70, 75, 80, 85, 88, 90, 82, 74],
        "precipitation_probability": [5, 10, 20, 15, 5, 0, 0, 10],
        "weathercode": [2, 2, 3, 1, 0, 0, 0, 1],
        "windspeed_10m": [14.2, 12.0, 10.5, 8.0, 7.5, 6.0, 9.0, 13.0],
        "surface_pressure": [1008.2] * 8,
        "visibility": [10000.0] * 8,
        "apparent_temperature": [36.0] * 8,
    },
    "daily": {
        "time": ["2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13", "2026-09-14"],
        "weathercode": [2, 2, 1, 0, 0],
        "temperature_2m_max": [33.0, 32.5, 33.5, 34.0, 33.8],
        "temperature_2m_min": [26.0, 25.5, 25.0, 26.2, 26.0],
        "precipitation_probability_max": [20, 15, 10, 5, 5],
        "windspeed_10m_max": [16.0, 14.5, 15.0, 13.0, 12.5],
    },
}


@pytest.fixture(autouse=True)
def clean_cache():
    clear_open_meteo_cache()
    yield
    clear_open_meteo_cache()


# 1. Successful Open-Meteo forecast fetching
@pytest.mark.asyncio
async def test_successful_open_meteo_forecast():
    provider = OpenMeteoProvider()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)

        assert isinstance(result, NormalizedWeatherResponse)
        assert result.location.name == "Chennai"
        assert result.current.temperature == 31.5
        assert len(result.forecast) > 0
        assert mock_get.call_count == 1


# 2. Cache hit avoids repeat upstream calls
@pytest.mark.asyncio
async def test_open_meteo_cache_hit():
    provider = OpenMeteoProvider()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        # First call: hits upstream
        res1 = await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)
        assert mock_get.call_count == 1

        # Second call: served from server-side cache
        res2 = await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)
        assert mock_get.call_count == 1  # No additional network call
        assert res1.current.temperature == res2.current.temperature
        assert "Cached" in res2.attribution_notes or "Open-Meteo" in res2.source


# 3. Cache expiration re-fetches from upstream
@pytest.mark.asyncio
async def test_open_meteo_cache_expiration():
    provider = OpenMeteoProvider()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        # First call: populates cache
        await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)
        assert mock_get.call_count == 1

        # Artificially age the cache entries beyond TTL
        assert len(_open_meteo_cache) > 0
        cache_key = list(_open_meteo_cache.keys())[0]
        _open_meteo_cache[cache_key].timestamp = time.time() - 700.0  # TTL is 600s

        # Second call: cache expired, triggers fresh upstream call
        await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)
        assert mock_get.call_count == 2


# 4. HTTP 429 retry with exponential backoff and recovery
@pytest.mark.asyncio
async def test_open_meteo_429_retry_recovery():
    provider = OpenMeteoProvider()

    # Create mock 429 response with Retry-After header
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "1"}

    # Create mock 200 response
    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = MOCK_OPEN_METEO_PAYLOAD

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # First attempt returns 429, second attempt succeeds with 200
        mock_get.side_effect = [mock_429, mock_200]

        result = await provider._fetch_with_retry(
            url=provider.FORECAST_URL,
            params={"latitude": 13.08, "longitude": 80.27},
            max_retries=2,
            initial_backoff=0.01,  # Fast backoff for testing
        )

        assert result["latitude"] == 13.08
        assert mock_get.call_count == 2


# 5. Persistent HTTP 429 produces structured UpstreamRateLimitError
@pytest.mark.asyncio
async def test_open_meteo_persistent_429_raises_structured_error():
    provider = OpenMeteoProvider()

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "5"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_429

        with pytest.raises(UpstreamRateLimitError) as exc_info:
            await provider._fetch_with_retry(
                url=provider.FORECAST_URL,
                params={"latitude": 13.08, "longitude": 80.27},
                max_retries=1,
                initial_backoff=0.01,
            )

        assert exc_info.value.retry_after == 5
        assert exc_info.value.provider == "Open-Meteo"
        assert "temporarily rate-limited" in str(exc_info.value)


# 6. Persistent 429 falls back to stale cache if available
@pytest.mark.asyncio
async def test_open_meteo_persistent_429_serves_stale_cache():
    provider = OpenMeteoProvider()

    # Pre-populate stale cache entry
    lat, lon, days = 13.0827, 80.2707, 5
    cache_key = f"forecast:{round(lat, 3)}:{round(lon, 3)}:{days}"
    stale_response = NormalizedWeatherResponse(
        location=LocationInfo(name="Chennai", country="IN", latitude=13.0827, longitude=80.2707),
        current=CurrentWeather(
            temperature=29.0,
            feels_like=33.0,
            humidity=75,
            wind_speed=10.0,
            wind_direction=90,
            condition="Partly cloudy",
            pressure=1010.0,
            visibility=9000.0,
            uv_index=5.0,
            updated_at="2026-09-10T11:00:00Z",
        ),
        forecast=[],
        source="Open-Meteo",
        attribution_notes="Initial baseline",
    )
    # Mark as expired (stale)
    _open_meteo_cache[cache_key] = CacheEntry(data=stale_response, timestamp=time.time() - 900.0, ttl=600.0)

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_429

        # Request should not raise 500 or crash; it falls back to stale telemetry with attribution warning
        result = await provider.get_forecast(city="Chennai", lat=lat, lon=lon, days=days)
        assert result.current.temperature == 29.0
        assert "rate-limit" in result.attribution_notes.lower()


# 7. Endpoint handles UpstreamRateLimitError with 503 instead of 500
def test_forecast_endpoint_returns_503_on_rate_limit():
    client = TestClient(app)

    with patch.object(
        OpenMeteoProvider,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=UpstreamRateLimitError(
            message="Open-Meteo public service is temporarily rate-limited",
            retry_after=10,
            provider="Open-Meteo",
        ),
    ):
        response = client.get("/api/v1/weather/forecast?city=Chennai&days=5&provider=open_meteo")
        assert response.status_code == 503
        assert response.headers.get("Retry-After") == "10"
        data = response.json()
        assert data["detail"]["status"] == "temporarily_unavailable"
        assert data["detail"]["provider"] == "Open-Meteo"
        assert data["detail"]["retry_after"] == 10


# 8. Duplicate / concurrent request protection coalesces identical in-flight requests
@pytest.mark.asyncio
async def test_concurrent_request_coalescing():
    call_count = 0

    async def slow_fetch():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"result": "success", "count": call_count}

    # Dispatch 5 identical concurrent calls through execute_coalesced
    tasks = [execute_coalesced("test_key_coalesce", slow_fetch) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # All 5 should receive the exact same result, and slow_fetch should execute exactly ONCE
    assert call_count == 1
    for res in results:
        assert res["result"] == "success"
        assert res["count"] == 1


# 9. NWP Common Model Forecast gracefully handles 429 without throwing
@pytest.mark.asyncio
async def test_open_meteo_common_forecast_429_graceful():
    provider = OpenMeteoProvider()

    with patch.object(
        provider,
        "_fetch_with_retry",
        side_effect=UpstreamRateLimitError(
            message="Rate limited",
            retry_after=5,
            provider="Open-Meteo",
        ),
    ):
        common_resp = await provider.get_common_forecast(lat=13.0827, lon=80.2707, days=5)
        assert common_resp.available is False
        assert "429" in common_resp.status
        assert common_resp.model == "ECMWF / Open-Meteo Multi-Model Ensemble"
