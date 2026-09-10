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


def _create_mock_grib2_response_bytes(temp_k=303.15, rh=65.0, u=3.0, v=4.0, pres=101200.0) -> bytes:
    """Builds synthetic GRIB2 binary subgrid messages containing TMP, RH, UGRD, VGRD, PRES."""
    import struct

    def _pack_subgrid(disc, cat, num, ref_val):
        s0 = b"GRIB\x00\x00" + bytes([disc, 2]) + struct.pack(">Q", 60)
        s4 = struct.pack(">IB", 16, 4) + b"\x00" * 4 + bytes([cat, num]) + b"\x00" * 5
        s5 = struct.pack(">IB", 20, 5) + b"\x00" * 6 + struct.pack(">f", ref_val) + b"\x00" * 4
        return s0 + s4 + s5 + b"7777"

    return (
        _pack_subgrid(0, 0, 0, temp_k)  # TMP 2m
        + _pack_subgrid(0, 1, 1, rh)     # RH 2m
        + _pack_subgrid(0, 2, 2, u)      # UGRD 10m
        + _pack_subgrid(0, 2, 3, v)      # VGRD 10m
        + _pack_subgrid(0, 3, 0, pres)   # PRES surface
    )


# 7. Test that parse_grib2_subgrid decodes Section 4 variables and Section 5 reference floats accurately
def test_parse_grib2_subgrid_decodes_variables():
    from app.providers.gfs_provider import parse_grib2_subgrid

    data = _create_mock_grib2_response_bytes(temp_k=303.15, rh=72.0, u=3.0, v=4.0, pres=101250.0)
    vars_dict = parse_grib2_subgrid(data)

    assert (0, 0, 0) in vars_dict
    assert abs(vars_dict[(0, 0, 0)] - 303.15) < 0.01
    assert abs(vars_dict[(0, 1, 1)] - 72.0) < 0.01
    assert abs(vars_dict[(0, 2, 2)] - 3.0) < 0.01
    assert abs(vars_dict[(0, 2, 3)] - 4.0) < 0.01
    assert abs(vars_dict[(0, 3, 0)] - 101250.0) < 1.0


# 8. GFS fallback does NOT call api.open-meteo.com/v1/gfs under any circumstance
@pytest.mark.asyncio
async def test_gfs_fallback_never_calls_open_meteo_endpoint():
    """
    CRITICAL ARCHITECTURAL GUARANTEE:
    Verifies that GFSProvider queries NOAA NOMADS (nomads.ncep.noaa.gov) and NEVER
    calls api.open-meteo.com/v1/gfs or any Open-Meteo URL when executing fallback.
    """
    provider = GFSProvider()
    assert provider.nomads_enabled is True

    captured_urls = []
    mock_grib_data = _create_mock_grib2_response_bytes(temp_k=303.15, rh=70.0)

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url, **kwargs):
            captured_urls.append(str(url))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = mock_grib_data
            return mock_resp

    with patch("httpx.AsyncClient", new=MockAsyncClient):
        res = await provider.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=2)

        assert len(captured_urls) > 0
        for url in captured_urls:
            # Must query official NOAA NOMADS
            assert "nomads.ncep.noaa.gov" in url
            # Must NEVER query Open-Meteo
            assert "api.open-meteo.com" not in url
            assert "open-meteo.com" not in url

        assert res.source == "NOAA Global Forecast System (GFS 0.25°) Fallback"
        assert res.location.name == "Chennai"
        # 303.15 K -> 30.0 C
        assert res.current.temperature == 30.0


# 9. End-to-end: Open-Meteo 429 triggers direct NOAA NOMADS fallback with correct schema
@pytest.mark.asyncio
async def test_end_to_end_open_meteo_429_triggers_direct_nomads_gfs():
    """
    End-to-end integration test:
    When Open-Meteo returns HTTP 429, WeatherService automatically falls back
    to GFSProvider via NOAA NOMADS, preserving NormalizedWeatherResponse schema
    with truthful source attribution and no fake data.
    """
    mock_grib_data = _create_mock_grib2_response_bytes(temp_k=304.65, rh=65.0, u=3.0, v=4.0, pres=101000.0)

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = mock_grib_data
            return mock_resp

    with patch.object(
        weather_service.open_meteo,
        "get_forecast",
        new_callable=AsyncMock,
        side_effect=UpstreamRateLimitError(
            message="Open-Meteo rate-limited (HTTP 429)", retry_after=30, provider="Open-Meteo"
        ),
    ), patch("httpx.AsyncClient", new=MockAsyncClient):
        res = await weather_service.get_forecast(city="Chennai", lat=13.0827, lon=80.2707, days=2)

        assert isinstance(res, NormalizedWeatherResponse)
        assert res.source == "NOAA Global Forecast System (GFS 0.25°) Fallback"
        assert "NOAA NCEP GFS 0.25°" in res.attribution_notes
        # 304.65 K - 273.15 = 31.5 C
        assert res.current.temperature == 31.5
        assert res.current.humidity == 65
        # Wind speed sqrt(3^2 + 4^2) = 5.0 m/s
        assert res.current.wind_speed == 5.0
        assert res.current.pressure == 1010.0
        assert len(res.forecast) > 0
        for f in res.forecast:
            assert f.condition_code in ["Clouds", "Rain", "Thunderstorm", "Clear"]

