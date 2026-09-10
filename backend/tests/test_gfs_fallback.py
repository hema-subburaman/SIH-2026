import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.weather_service import weather_service
from app.services.forecast_service import forecast_service
from app.providers.open_meteo import OpenMeteoProvider
from app.providers.gfs_provider import GFSProvider, clear_gfs_cache
from app.providers.base import UpstreamRateLimitError
from app.schemas.weather import (
    NormalizedWeatherResponse,
    DetailedForecastResponse,
    LocationInfo,
    CurrentWeather,
    ForecastItem,
)
from app.schemas.forecast_common import CommonForecastItem, CommonModelForecastResponse


def _create_mock_open_meteo_response():
    return NormalizedWeatherResponse(
        location=LocationInfo(name="Chennai", state="Tamil Nadu", country="IN", latitude=13.0827, longitude=80.2707),
        current=CurrentWeather(
            temperature=31.0,
            feels_like=35.0,
            humidity=70,
            wind_speed=4.0,
            condition="Partly cloudy",
            condition_code="Clouds",
            pressure=1009.0,
        ),
        forecast=[
            ForecastItem(
                time="2026-09-11 12:00:00",
                temperature=32.0,
                humidity=65,
                wind_speed=4.5,
                condition="Partly cloudy",
                condition_code="Clouds",
                pop=0.1,
            ),
            ForecastItem(
                time="2026-09-12 12:00:00",
                temperature=33.0,
                humidity=60,
                wind_speed=3.8,
                condition="Clear sky",
                condition_code="Clear",
                pop=0.0,
            ),
        ],
        source="Open-Meteo NWP Forecast Service",
        attribution_notes="Standard Open-Meteo model output.",
        cached=False,
    )


def _create_mock_gfs_response():
    return NormalizedWeatherResponse(
        location=LocationInfo(name="Chennai", state="Tamil Nadu", country="IN", latitude=13.0827, longitude=80.2707),
        current=CurrentWeather(
            temperature=30.5,
            feels_like=34.0,
            humidity=72,
            wind_speed=4.2,
            condition="GFS Model Forecast",
            condition_code="Clouds",
            pressure=1010.0,
        ),
        forecast=[
            ForecastItem(
                time="2026-09-11 12:00:00",
                temperature=31.5,
                humidity=68,
                wind_speed=4.0,
                condition="GFS Model Forecast",
                condition_code="Clouds",
                pop=0.2,
            ),
            ForecastItem(
                time="2026-09-12 12:00:00",
                temperature=32.5,
                humidity=65,
                wind_speed=3.5,
                condition="GFS Model Forecast",
                condition_code="Clouds",
                pop=0.1,
            ),
            ForecastItem(
                time="2026-09-13 12:00:00",
                temperature=33.0,
                humidity=60,
                wind_speed=4.0,
                condition="Thunderstorm Risk",
                condition_code="Thunderstorm",
                pop=0.7,
                rain_mm=4.5,
            ),
        ],
        source="NOAA Global Forecast System (GFS 0.25°) Fallback",
        attribution_notes="Operational NOAA NCEP GFS 0.25° NWP numerical model forecast (automatic fallback from Open-Meteo).",
        cached=False,
    )


@pytest.fixture(autouse=True)
def reset_caches():
    clear_gfs_cache()
    yield
    clear_gfs_cache()


# 1. Open-Meteo success -> returns Open-Meteo result (GFS is not called)
@pytest.mark.asyncio
async def test_open_meteo_success_returns_open_meteo_result():
    mock_om = _create_mock_open_meteo_response()

    with patch.object(weather_service.open_meteo, "get_forecast", new_callable=AsyncMock) as mock_om_call, \
         patch.object(weather_service.gfs, "get_forecast", new_callable=AsyncMock) as mock_gfs_call:
        mock_om_call.return_value = mock_om

        res = await weather_service.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)

        assert res.location.name == "Chennai"
        assert res.current.temperature == 31.0
        assert "Open-Meteo" in res.source
        assert mock_om_call.call_count == 1
        assert mock_gfs_call.call_count == 0  # GFS was not needed


# 2. Open-Meteo 429 rate-limited -> triggers GFS fallback
@pytest.mark.asyncio
async def test_open_meteo_429_triggers_gfs_fallback():
    mock_gfs = _create_mock_gfs_response()

    with patch.object(
        weather_service.open_meteo,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=UpstreamRateLimitError(
            message="Open-Meteo rate-limited (HTTP 429)", retry_after=10, provider="Open-Meteo"
        ),
    ) as mock_om_call, patch.object(
        weather_service.gfs, "get_forecast", new_callable=AsyncMock
    ) as mock_gfs_call:
        mock_gfs_call.return_value = mock_gfs

        res = await weather_service.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)

        assert mock_om_call.call_count == 1
        assert mock_gfs_call.call_count == 1
        assert "GFS" in res.source or "NOAA" in res.source
        assert "Fallback" in res.source
        assert res.current.temperature == 30.5
        assert len(res.forecast) == 3


# 3. Open-Meteo general failure (timeout, 5xx) -> triggers GFS fallback
@pytest.mark.asyncio
async def test_open_meteo_failure_triggers_gfs_fallback():
    mock_gfs = _create_mock_gfs_response()

    with patch.object(
        weather_service.open_meteo,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectTimeout("Open-Meteo upstream connection timed out"),
    ), patch.object(weather_service.gfs, "get_forecast", new_callable=AsyncMock) as mock_gfs_call:
        mock_gfs_call.return_value = mock_gfs

        res = await weather_service.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)

        assert mock_gfs_call.call_count == 1
        assert "GFS" in res.source
        assert res.location.name == "Chennai"


# 4. Open-Meteo failure + GFS unavailable -> returns structured 503 response
def test_open_meteo_failure_and_gfs_unavailable_returns_503():
    client = TestClient(app)

    with patch.object(
        OpenMeteoProvider,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=UpstreamRateLimitError(
            message="Open-Meteo rate-limited", retry_after=15, provider="Open-Meteo"
        ),
    ), patch.object(
        GFSProvider,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=UpstreamRateLimitError(
            message="GFS unavailable", retry_after=15, provider="NOAA GFS"
        ),
    ):
        response = client.get("/api/v1/weather/forecast?city=Chennai&days=5")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "temporarily_unavailable"
        assert response.headers.get("Retry-After") is not None


# 5. Response schema remains compatible with detailed forecast and frontend consumers
@pytest.mark.asyncio
async def test_response_schema_compatibility_with_detailed_forecast():
    mock_gfs = _create_mock_gfs_response()

    with patch.object(
        weather_service.open_meteo,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=UpstreamRateLimitError(message="429 Too Many Requests", retry_after=5, provider="Open-Meteo"),
    ), patch.object(weather_service.gfs, "get_forecast", new_callable=AsyncMock) as mock_gfs_call:
        mock_gfs_call.return_value = mock_gfs

        # detailed forecast calls weather_service.get_forecast internally
        detailed_res = await forecast_service.get_detailed_forecast(city="Chennai", days=5)

        assert isinstance(detailed_res, DetailedForecastResponse)
        assert detailed_res.location.name == "Chennai"
        assert "GFS" in detailed_res.source or "NOAA" in detailed_res.source
        assert len(detailed_res.days) > 0
        for day in detailed_res.days:
            assert day.temp_max >= day.temp_min
            assert day.event_suitability_label in ["Optimal", "Favorable", "Moderate Caution", "Unfavorable / High Risk"]


# 6. GFSProvider directly normalizes CommonModelForecastResponse and caches result
@pytest.mark.asyncio
async def test_gfs_provider_get_forecast_direct_and_caching():
    provider = GFSProvider()

    mock_items = [
        CommonForecastItem(
            provider="gfs",
            model="NOAA GFS 0.25°",
            source="NOAA NCEP",
            forecast_time="2026-09-11T12:00:00",
            latitude=13.08,
            longitude=80.27,
            temperature=29.5,
            feels_like=33.0,
            humidity=70,
            precipitation=0.0,
            wind_speed=4.2,
            wind_direction=80.0,
            pressure=1012.0,
            condition="Partly cloudy",
        ),
        CommonForecastItem(
            provider="gfs",
            model="NOAA GFS 0.25°",
            source="NOAA NCEP",
            forecast_time="2026-09-11T15:00:00",
            latitude=13.08,
            longitude=80.27,
            temperature=31.0,
            feels_like=35.0,
            humidity=65,
            precipitation=1.5,
            wind_speed=5.0,
            wind_direction=90.0,
            pressure=1010.0,
            condition="Rain Showers",
        ),
    ]

    mock_common = CommonModelForecastResponse(
        provider="gfs",
        model="NOAA GFS 0.25°",
        source="NOAA NCEP",
        available=True,
        configured=True,
        status="Active",
        latitude=13.08,
        longitude=80.27,
        forecast_items=mock_items,
    )

    with patch.object(provider, "get_common_forecast", new_callable=AsyncMock) as mock_common_call:
        mock_common_call.return_value = mock_common

        # First call: hits get_common_forecast
        resp1 = await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)
        assert mock_common_call.call_count == 1
        assert resp1.location.name == "Chennai"
        assert resp1.current.temperature == 29.5
        assert len(resp1.forecast) == 2
        assert resp1.source == "NOAA Global Forecast System (GFS 0.25°) Fallback"

        # Second call: served from GFS cache
        resp2 = await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=5)
        assert mock_common_call.call_count == 1  # No additional network call
        assert resp2.cached is True
