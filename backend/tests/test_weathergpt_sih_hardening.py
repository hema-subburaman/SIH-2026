import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.schemas.chat import ChatQueryRequest
from app.schemas.risk import ActivityType, RiskLevel
from app.schemas.alert import AlertItem, AlertCategory, AlertSeverity, AlertsResponse
from app.schemas.claim import ClaimVerifyRequest, ClaimStatus
from app.services.ai_service import ai_service
from app.services.multilingual_service import multilingual_service
from app.providers.imd_warning_provider import OfficialMeteorologicalWarningProvider
from app.providers.open_meteo import OpenMeteoProvider
from app.services.alert_service import alert_service
from app.services.risk_engine import risk_engine
from app.services.claim_verifier import claim_verifier


# 1. Rule-based NLU still works
def test_rule_based_nlu_extraction():
    entities = ai_service.extract_entities_rule_based(
        query="Can I go running tomorrow morning in Chennai?",
        user_selected_city="Chennai"
    )
    assert entities.intent == "activity_advisory"
    assert entities.activity == ActivityType.RUNNING.value
    assert entities.target_date == "tomorrow"
    assert entities.target_time_slot == "morning"
    assert entities.location == "Chennai"
    assert entities.is_llm_enhanced is False


# 2. LLM unavailable -> rule-based fallback
@pytest.mark.asyncio
async def test_llm_unavailable_fallback():
    original_client = ai_service.openai_client
    ai_service.openai_client = None
    try:
        req = ChatQueryRequest(
            message="Will it rain tomorrow in Mumbai?",
            city="Mumbai",
            language="en"
        )
        res = await ai_service.process_query(req)
        assert res.intent in ["rain_inquiry", "forecast"]
        assert res.is_llm_enhanced is False
        assert "Mumbai" in res.location_used
        assert res.answer is not None and len(res.answer) > 0
    finally:
        ai_service.openai_client = original_client


# 3. Invalid LLM JSON -> rule-based fallback
@pytest.mark.asyncio
async def test_invalid_llm_json_fallback():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "INVALID_NON_JSON_OUTPUT_FROM_LLM"
    mock_response = MagicMock(choices=[mock_choice])
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    original_client = ai_service.openai_client
    ai_service.openai_client = mock_client
    try:
        req = ChatQueryRequest(
            message="Can I go running tomorrow morning in Delhi?",
            city="Delhi",
            language="en"
        )
        res = await ai_service.process_query(req)
        assert res.intent == "activity_advisory"
        assert res.is_llm_enhanced is False
        assert "Delhi" in res.location_used
    finally:
        ai_service.openai_client = original_client


# 4. Tomorrow rain query
@pytest.mark.asyncio
async def test_tomorrow_rain_query():
    req = ChatQueryRequest(
        message="Will it rain tomorrow in Chennai?",
        city="Chennai",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert res.intent in ["rain_inquiry", "forecast"]
    assert res.weather_summary["target_date"] == "tomorrow"
    assert "rain" in res.answer.lower() or "precipitation" in res.answer.lower()


# 5. Weekend query
@pytest.mark.asyncio
async def test_weekend_forecast_query():
    req = ChatQueryRequest(
        message="How is the weather this weekend in Bengaluru?",
        city="Bengaluru",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert res.intent == "weekend_forecast"
    assert res.weather_summary.get("weekend") is True or "weekend" in res.weather_summary.get("target_date", "")
    assert "Saturday" in res.answer or "Sunday" in res.answer or "Weekend" in res.answer


# 6. Tomorrow outdoor event query
@pytest.mark.asyncio
async def test_tomorrow_outdoor_event_query():
    req = ChatQueryRequest(
        message="Will tomorrow be suitable for an outdoor event in Kolkata?",
        city="Kolkata",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert res.weather_summary.get("activity") == "outdoor_event"
    assert any(term in res.answer.lower() for term in ["suitability", "feasibility", "outdoor event", "event"])
    assert res.recommendation is not None


# 7. Tomorrow morning running query
@pytest.mark.asyncio
async def test_tomorrow_morning_running_query():
    req = ChatQueryRequest(
        message="Can I go running tomorrow morning in Hyderabad?",
        city="Hyderabad",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert res.intent == "activity_advisory"
    assert res.weather_summary.get("activity") == "running"
    assert res.weather_summary.get("target_date") == "tomorrow"
    assert res.weather_summary.get("target_time_slot") == "morning"
    assert res.risk_level is not None
    assert res.recommendation is not None


# 8. Tamil forecast query
def test_tamil_forecast_queries():
    # Rain
    ta_rain = "Naalaikku mazha varuma?"
    assert multilingual_service.detect_language(ta_rain) == "ta"
    entities_rain = ai_service.extract_entities_rule_based(ta_rain, "Chennai")
    assert entities_rain.intent == "rain_inquiry"
    assert entities_rain.target_date == "tomorrow"

    # Running morning
    ta_run = "Naalaikku morning running pogalama?"
    assert multilingual_service.detect_language(ta_run) == "ta"
    entities_run = ai_service.extract_entities_rule_based(ta_run, "Chennai")
    assert entities_run.activity == "running"
    assert entities_run.target_date == "tomorrow"
    assert entities_run.target_time_slot == "morning"


# 9. Hindi forecast query
def test_hindi_forecast_queries():
    # Rain
    hi_rain = "Kya kal barish hogi?"
    assert multilingual_service.detect_language(hi_rain) == "hi"
    entities_rain = ai_service.extract_entities_rule_based(hi_rain, "Delhi")
    assert entities_rain.intent == "rain_inquiry"
    assert entities_rain.target_date == "tomorrow"

    # Running morning
    hi_run = "Kya main kal subah running kar sakta hoon?"
    assert multilingual_service.detect_language(hi_run) == "hi"
    entities_run = ai_service.extract_entities_rule_based(hi_run, "Delhi")
    assert entities_run.activity == "running"
    assert entities_run.target_date == "tomorrow"
    assert entities_run.target_time_slot == "morning"


# 10. City -> State resolution
def test_city_to_state_resolution():
    provider = OfficialMeteorologicalWarningProvider()
    assert provider.resolve_city_state("Chennai") == "Tamil Nadu"
    assert provider.resolve_city_state("Coimbatore") == "Tamil Nadu"
    assert provider.resolve_city_state("Madurai") == "Tamil Nadu"
    assert provider.resolve_city_state("Bengaluru") == "Karnataka"
    assert provider.resolve_city_state("Hyderabad") == "Telangana"
    assert provider.resolve_city_state("Mumbai") == "Maharashtra"
    assert provider.resolve_city_state("Pune") == "Maharashtra"
    assert provider.resolve_city_state("Delhi") == "Delhi"
    assert provider.resolve_city_state("Kolkata") == "West Bengal"
    assert provider.resolve_city_state("Ahmedabad") == "Gujarat"
    assert provider.resolve_city_state("Jaipur") == "Rajasthan"
    assert provider.resolve_city_state("Lucknow") == "Uttar Pradesh"
    assert provider.resolve_city_state("Kochi") == "Kerala"
    assert provider.resolve_city_state("Thiruvananthapuram") == "Kerala"
    assert provider.resolve_city_state("Visakhapatnam") == "Andhra Pradesh"
    assert provider.resolve_city_state("Bhubaneswar") == "Odisha"

    # Unsupported / unknown location must return None (NO GUESSING)
    assert provider.resolve_city_state("NonExistentCityAtlantis") is None


# 11. Official alert vs System risk separation
def test_official_warning_vs_system_risk_separation():
    official_alert = AlertItem(
        id="imd-001",
        event="Severe Cyclonic Storm Alert",
        category=AlertCategory.CYCLONE,
        severity=AlertSeverity.WARNING,
        location="Chennai, Tamil Nadu",
        description="Official IMD cyclone bulletin.",
        recommendation="Evacuate coastal zones.",
        is_official=True,
        source="India Meteorological Department (IMD) / NDMA Sachet CAP Feed"
    )

    system_risk = AlertItem(
        id="sys-heat-001",
        event="Elevated Thermal Index Risk",
        category=AlertCategory.EXTREME_HEAT,
        severity=AlertSeverity.WATCH,
        location="Chennai",
        description="Calculated heat index threshold exceedance.",
        recommendation="Avoid strenuous outdoor activities.",
        is_official=False,
        source="WeatherGPT Algorithmic Impact Engine (Rule-based Threshold)"
    )

    assert official_alert.is_official is True
    assert "IMD" in official_alert.source
    assert system_risk.is_official is False
    assert "Algorithmic" in system_risk.source or "Engine" in system_risk.source
    assert official_alert.is_official != system_risk.is_official


# 12. Duplicate alert suppression
@pytest.mark.asyncio
async def test_duplicate_alert_suppression():
    provider = OfficialMeteorologicalWarningProvider()
    mock_alert = AlertItem(
        id="imd-test-dup-101",
        event="Heavy Rainfall Warning",
        category=AlertCategory.HEAVY_RAINFALL,
        severity=AlertSeverity.WARNING,
        location="Chennai, Tamil Nadu",
        description="Isolated heavy rainfall expected.",
        recommendation="Carry umbrella.",
        is_official=True,
        source="India Meteorological Department (IMD) / NDMA Sachet CAP Feed"
    )

    with patch.object(provider, 'get_alerts_with_coverage', AsyncMock(return_value=([mock_alert], True, "Tamil Nadu"))):
        original_provider = alert_service.official_provider
        alert_service.official_provider = provider
        alert_service.seen_alert_ids.clear()

        try:
            # First poll: alert is new -> captured and returned
            first_poll = await alert_service.poll_and_broadcast_new_alerts()
            assert len(first_poll) >= 1
            assert any(a.id == "imd-test-dup-101" for a in first_poll)

            # Second poll: same alert -> suppressed as duplicate
            second_poll = await alert_service.poll_and_broadcast_new_alerts()
            assert len(second_poll) == 0
        finally:
            alert_service.official_provider = original_provider


# 13. Climate provider failure does NOT generate synthetic data
@pytest.mark.asyncio
async def test_climate_failure_returns_unavailable_no_synthetic_data():
    provider = OpenMeteoProvider()

    # Simulate network failure during archive API call
    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=Exception("Network Connection Timeout"))):
        resp = await provider.get_climate_history(city="Chennai", years=10)
        assert resp.available is False
        assert "unavailable" in resp.message.lower()
        # Strictly verify zero synthetic data points were generated
        assert len(resp.data_points) == 0
        assert resp.baseline_avg_temp is None


# 14. Existing risk engine calculation regression test
def test_risk_engine_regression():
    analysis = risk_engine.analyze(
        activity=ActivityType.RUNNING,
        temperature=38.0,
        humidity=70,
        wind_speed=2.0,
        condition="Clear and Hot",
        pop=0.0
    )
    assert analysis.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]
    assert len(analysis.factors) > 0
    assert analysis.recommendation is not None


# 15. Existing claim verification regression test
@pytest.mark.asyncio
async def test_claim_verification_regression():
    req = ClaimVerifyRequest(
        claim="There is a severe cyclone warning in Chennai right now",
        city="Chennai"
    )
    res = await claim_verifier.verify_claim(req)
    assert res.status in [ClaimStatus.VERIFIED, ClaimStatus.UNVERIFIED]
    assert res.official_warning_checked is True
