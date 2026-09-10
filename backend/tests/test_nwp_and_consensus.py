import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.providers.gfs_provider import GFSProvider
from app.providers.wrf_provider import WRFProvider
from app.schemas.forecast_common import CommonForecastItem, CommonModelForecastResponse
from app.services.model_comparison_service import ModelComparisonService
from app.ingestion.base_ingestor import BaseIngestor, IngestionResult
from app.ingestion.validator import MeteorologicalValidator
from app.ingestion.scheduler import IngestionScheduler
from app.services.advisory_service import advisory_engine, DISCLAIMER_NOTICE


# ==========================================
# 1. GFS PROVIDER TESTS
# ==========================================

@pytest.mark.asyncio
async def test_gfs_unconfigured_state():
    """GFS should return structured unavailable state when unconfigured, with zero fake data."""
    with patch.dict("os.environ", {"GFS_NWP_ENDPOINT": "", "GFS_FILE_PATH": "", "GFS_NOMADS_ENABLED": "false"}):
        provider = GFSProvider()
        assert not provider.is_configured
        
        info = await provider.get_model_run_info()
        assert info["configured"] is False
        assert info["available"] is False
        assert "Provider not configured" in info["status"]

        common = await provider.get_common_forecast(lat=13.08, lon=80.27)
        assert common.available is False
        assert len(common.forecast_items) == 0
        assert "unavailable" in common.status.lower()


@pytest.mark.asyncio
async def test_gfs_configured_failure_returns_unavailable():
    """GFS should never invent data if an endpoint is unreachable."""
    with patch.dict("os.environ", {"GFS_NWP_ENDPOINT": "http://127.0.0.1:9999/invalid_gfs", "GFS_NOMADS_ENABLED": "false"}):
        provider = GFSProvider()
        assert provider.is_configured
        
        # When network request fails, return structured unavailable state
        common = await provider.get_common_forecast(lat=13.08, lon=80.27)
        assert common.available is False
        assert len(common.forecast_items) == 0


@pytest.mark.asyncio
async def test_gfs_normalization_valid_data():
    """GFS should correctly normalize incoming numerical items into common schema."""
    provider = GFSProvider()
    
    mock_items = [
        CommonForecastItem(
            provider="gfs",
            model="NOAA GFS 0.25°",
            source="NOAA NCEP",
            forecast_time="2026-09-11T00:00:00",
            latitude=13.08,
            longitude=80.27,
            temperature=29.5,
            humidity=70,
            precipitation=0.0,
            wind_speed=4.2,
            cape=1200.0,
            available_variables=["temperature", "humidity", "precipitation", "wind_speed", "cape"],
        )
    ]

    with patch.object(provider, "get_common_forecast", new_callable=AsyncMock) as mock_method:
        mock_method.return_value = CommonModelForecastResponse(
            provider="gfs",
            model="NOAA GFS 0.25°",
            source="NOAA NCEP",
            available=True,
            configured=True,
            status="Active",
            resolution="0.25°",
            forecast_items=mock_items,
        )

        resp = await provider.get_common_forecast(lat=13.08, lon=80.27)
        assert resp.available is True
        assert len(resp.forecast_items) == 1
        item = resp.forecast_items[0]
        assert item.temperature == 29.5
        assert item.cape == 1200.0
        assert "cape" in item.available_variables


# ==========================================
# 2. WRF PROVIDER TESTS
# ==========================================

@pytest.mark.asyncio
async def test_wrf_unconfigured_state():
    """WRF provider must return structured unconfigured state when endpoints/files are absent."""
    with patch.dict("os.environ", {"WRF_MODEL_ENDPOINT": "", "WRF_NETCDF_PATH": ""}):
        provider = WRFProvider()
        assert not provider.is_configured

        info = await provider.get_model_run_info()
        assert info["configured"] is False
        assert info["available"] is False
        assert "Provider not configured" in info["status"]

        common = await provider.get_common_forecast(lat=13.08, lon=80.27)
        assert common.available is False
        assert common.configured is False
        assert "not configured" in common.status.lower()
        assert len(common.forecast_items) == 0


@pytest.mark.asyncio
async def test_wrf_missing_netcdf_file():
    """WRF configured with missing NetCDF file returns unavailable rather than crashing."""
    with patch.dict("os.environ", {"WRF_NETCDF_PATH": "/path/to/non_existent_wrfout.nc", "WRF_MODEL_ENDPOINT": ""}):
        provider = WRFProvider()
        common = await provider.get_common_forecast(lat=13.08, lon=80.27)
        assert common.available is False
        assert len(common.forecast_items) == 0


# ==========================================
# 3. MODEL COMPARISON & CONSENSUS TESTS
# ==========================================

@pytest.mark.asyncio
async def test_model_comparison_single_provider_no_synthetic_confidence():
    """If only 1 model is available, consensus confidence must state single-provider and agreement score must be None."""
    service = ModelComparisonService()

    # Mock Open-Meteo available, others unavailable
    mock_open_meteo = CommonModelForecastResponse(
        provider="open_meteo",
        model="ECMWF Ensemble",
        source="Open-Meteo",
        available=True,
        configured=True,
        status="Active",
        forecast_items=[
            CommonForecastItem(
                provider="open_meteo",
                model="ECMWF Ensemble",
                source="Open-Meteo",
                forecast_time="2026-09-11T12:00:00",
                latitude=13.08,
                longitude=80.27,
                temperature=30.0,
                precipitation=0.0,
                wind_speed=3.5,
            )
        ]
    )
    unavailable_resp = CommonModelForecastResponse(
        provider="unavailable",
        model="Unavailable Model",
        source="Test",
        available=False,
        configured=False,
        status="Provider not configured",
        forecast_items=[]
    )

    with patch.object(service.open_meteo, "get_common_forecast", AsyncMock(return_value=mock_open_meteo)), \
         patch.object(service.gfs, "get_common_forecast", AsyncMock(return_value=unavailable_resp)), \
         patch.object(service.wrf, "get_common_forecast", AsyncMock(return_value=unavailable_resp)), \
         patch.object(service.openweather, "get_common_forecast", AsyncMock(return_value=unavailable_resp)):

        comp = await service.compare_forecasts(lat=13.08, lon=80.27, location_name="Chennai")
        assert comp.models_available_count == 1
        assert comp.consensus_status == "SINGLE_PROVIDER"
        assert comp.agreement_score is None  # Never invent confidence!
        assert "Single-provider forecast" in comp.confidence


@pytest.mark.asyncio
async def test_model_comparison_agreement_high():
    """When multiple models closely agree on temperature and precipitation, agreement score is high."""
    service = ModelComparisonService()

    time_str = "2026-09-11T12:00:00"
    m1_resp = CommonModelForecastResponse(
        provider="open_meteo",
        model="ECMWF",
        source="Open-Meteo",
        available=True,
        forecast_items=[
            CommonForecastItem(
                provider="open_meteo", model="ECMWF", source="Open-Meteo",
                forecast_time=time_str, latitude=13.08, longitude=80.27,
                temperature=30.0, precipitation=0.0, wind_speed=3.0,
            )
        ]
    )
    m2_resp = CommonModelForecastResponse(
        provider="gfs",
        model="NOAA GFS",
        source="NOAA",
        available=True,
        forecast_items=[
            CommonForecastItem(
                provider="gfs", model="NOAA GFS", source="NOAA",
                forecast_time=time_str, latitude=13.08, longitude=80.27,
                temperature=30.8, precipitation=0.0, wind_speed=3.4,
            )
        ]
    )
    unavail = CommonModelForecastResponse(provider="none", model="none", source="none", available=False, forecast_items=[])

    with patch.object(service.open_meteo, "get_common_forecast", AsyncMock(return_value=m1_resp)), \
         patch.object(service.gfs, "get_common_forecast", AsyncMock(return_value=m2_resp)), \
         patch.object(service.wrf, "get_common_forecast", AsyncMock(return_value=unavail)), \
         patch.object(service.openweather, "get_common_forecast", AsyncMock(return_value=unavail)):

        comp = await service.compare_forecasts(lat=13.08, lon=80.27, location_name="Chennai")
        assert comp.models_available_count == 2
        assert comp.consensus_status == "CONSENSUS_AVAILABLE"
        assert comp.agreement_score is not None
        assert comp.agreement_score >= 0.85
        assert comp.confidence == "High"
        assert len(comp.disagreements) == 0


@pytest.mark.asyncio
async def test_model_comparison_disagreement_detection():
    """Detects and explicitly reports precipitation and temperature disagreements between models."""
    service = ModelComparisonService()

    time_str = "2026-09-11T12:00:00"
    # Model 1 predicts heavy rain (15mm)
    m1_resp = CommonModelForecastResponse(
        provider="open_meteo",
        model="ECMWF",
        source="Open-Meteo",
        available=True,
        forecast_items=[
            CommonForecastItem(
                provider="open_meteo", model="ECMWF", source="Open-Meteo",
                forecast_time=time_str, latitude=13.08, longitude=80.27,
                temperature=24.0, precipitation=15.0, wind_speed=4.0,
            )
        ]
    )
    # Model 2 predicts dry (0.0mm) and hotter (32°C)
    m2_resp = CommonModelForecastResponse(
        provider="gfs",
        model="NOAA GFS",
        source="NOAA",
        available=True,
        forecast_items=[
            CommonForecastItem(
                provider="gfs", model="NOAA GFS", source="NOAA",
                forecast_time=time_str, latitude=13.08, longitude=80.27,
                temperature=32.0, precipitation=0.0, wind_speed=4.5,
            )
        ]
    )
    unavail = CommonModelForecastResponse(provider="none", model="none", source="none", available=False, forecast_items=[])

    with patch.object(service.open_meteo, "get_common_forecast", AsyncMock(return_value=m1_resp)), \
         patch.object(service.gfs, "get_common_forecast", AsyncMock(return_value=m2_resp)), \
         patch.object(service.wrf, "get_common_forecast", AsyncMock(return_value=unavail)), \
         patch.object(service.openweather, "get_common_forecast", AsyncMock(return_value=unavail)):

        comp = await service.compare_forecasts(lat=13.08, lon=80.27, location_name="Chennai")
        assert comp.models_available_count == 2
        assert comp.confidence in ("Moderate", "Low")
        assert len(comp.disagreements) > 0
        # Disagreement must mention precipitation or temperature
        dis_text = " ".join(comp.disagreements)
        assert "precipitation" in dis_text.lower() or "temperature" in dis_text.lower()


# ==========================================
# 4. INGESTION PIPELINE TESTS
# ==========================================

@pytest.mark.asyncio
async def test_validator_physical_bounds():
    """Validator rejects impossible physical values."""
    # Valid observation
    valid, errors = MeteorologicalValidator.validate_observation({
        "temperature": 28.5,
        "humidity": 65,
        "wind_speed": 4.0,
        "pressure": 1012.0,
    })
    assert valid is True
    assert len(errors) == 0

    # Impossible temperature (120°C)
    invalid_temp, errors_temp = MeteorologicalValidator.validate_observation({"temperature": 120.0})
    assert invalid_temp is False
    assert any("Temperature out of physical bounds" in e for e in errors_temp)

    # Impossible humidity (-10%)
    invalid_h, errors_h = MeteorologicalValidator.validate_observation({"humidity": -10})
    assert invalid_h is False

    # Impossible wind speed (500 m/s)
    invalid_w, errors_w = MeteorologicalValidator.validate_observation({"wind_speed": 500.0})
    assert invalid_w is False


@pytest.mark.asyncio
async def test_validator_deduplication():
    """Validator successfully removes duplicate timestamped records."""
    records = [
        {"time": "2026-09-11T00:00:00", "temp": 28.0},
        {"time": "2026-09-11T00:00:00", "temp": 28.1},  # Duplicate
        {"time": "2026-09-11T03:00:00", "temp": 27.5},
    ]
    deduped = MeteorologicalValidator.deduplicate_records(records, key_field="time")
    assert len(deduped) == 2


@pytest.mark.asyncio
async def test_base_ingestor_retry_and_backoff():
    """BaseIngestor retries on failure with exponential backoff and encapsulates errors gracefully."""
    class FailingIngestor(BaseIngestor):
        def __init__(self):
            super().__init__(name="TestFail", provider="test", timeout_seconds=1.0, max_retries=1, backoff_factor=0.01)
            self.attempts = 0

        async def fetch_and_parse(self, **kwargs):
            self.attempts += 1
            raise ConnectionError("Upstream connection refused")

    worker = FailingIngestor()
    res = await worker.run()
    assert res.success is False
    assert res.records_ingested == 0
    assert "FAILED" in res.status
    assert worker.attempts == 2  # 1 initial + 1 retry


@pytest.mark.asyncio
async def test_ingestion_scheduler_fault_isolation():
    """One failed worker does NOT bring down the rest of the ingestion pipeline."""
    scheduler = IngestionScheduler()

    # Mock weather succeeding, gfs failing
    async def mock_weather_run(*args, **kwargs):
        return IngestionResult(job_name="weather", provider="weather", success=True, status="SUCCESS", records_ingested=1)

    async def mock_gfs_run(*args, **kwargs):
        return IngestionResult(job_name="gfs", provider="gfs", success=False, status="FAILED: GFS unavailable", records_ingested=0)

    with patch.object(scheduler.weather_worker, "run", side_effect=mock_weather_run), \
         patch.object(scheduler.gfs_worker, "run", side_effect=mock_gfs_run):

        results = await scheduler.run_all(city="Chennai")
        assert results["weather"].success is True
        assert results["gfs"].success is False
        assert "weather" in results and "alerts" in results


# ==========================================
# 5. USE-CASE ADVISORY ENGINE TESTS
# ==========================================

def test_advisory_agriculture_spray_and_rain():
    """High wind advises against pesticide spraying; rain triggers irrigation suspension."""
    # High wind > 5.5 m/s
    res_wind = advisory_engine.evaluate(
        persona="farmer",
        city="Coimbatore",
        temp=28.0,
        humidity=65,
        wind_speed=7.0,
        precip_mm=0.0
    )
    assert res_wind.persona == "agriculture"
    assert any("spraying" in r.lower() for r in res_wind.actionable_recommendations)
    assert res_wind.decision_threshold_label == DISCLAIMER_NOTICE

    # Heavy rain
    res_rain = advisory_engine.evaluate(
        persona="farmer",
        city="Thanjavur",
        temp=26.0,
        humidity=90,
        wind_speed=3.0,
        precip_mm=12.0,
        pop=0.85
    )
    assert res_rain.decision in ("CAUTION", "SUSPEND")
    assert any("irrigation" in r.lower() for r in res_rain.actionable_recommendations)


def test_advisory_marine_rough_sea():
    """Wind >= 12 m/s advises fishermen to suspend venturing into the sea."""
    res = advisory_engine.evaluate(
        persona="fisherman",
        city="Rameswaram",
        temp=29.0,
        humidity=80,
        wind_speed=14.0,  # ~50 km/h gale
        precip_mm=5.0
    )
    assert res.persona == "marine"
    assert res.decision == "SUSPEND"
    assert any("not to venture" in r.lower() for r in res.actionable_recommendations)


def test_advisory_construction_crane_safety():
    """High wind >= 10 m/s warns tower crane operators to halt lift operations."""
    res = advisory_engine.evaluate(
        persona="construction",
        city="Bengaluru",
        temp=31.0,
        humidity=60,
        wind_speed=11.5,
        precip_mm=0.0
    )
    assert res.persona == "construction"
    assert res.decision in ("SUSPEND", "CAUTION")
    assert any("crane" in r.lower() for r in res.actionable_recommendations)


def test_advisory_aviation_briefing():
    """Low visibility and high CAPE trigger aviation caution / IFR recommendations."""
    res = advisory_engine.evaluate(
        persona="aviation",
        city="Delhi",
        temp=33.0,
        humidity=75,
        wind_speed=6.0,
        visibility=1500.0,  # < 3000m marginal VFR
        cape=1800.0         # Severe convective instability
    )
    assert res.persona == "aviation"
    assert res.decision in ("CAUTION", "SUSPEND")
    assert any("vfr" in r.lower() or "instrument" in r.lower() for r in res.actionable_recommendations)
    assert any("cape" in str(f.get("factor", "")).lower() for f in res.critical_factors)
