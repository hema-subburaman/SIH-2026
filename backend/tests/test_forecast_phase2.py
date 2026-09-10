import pytest
from app.services.forecast_service import forecast_service
from app.services.ai_service import ai_service
from app.schemas.chat import ChatQueryRequest


def test_calculate_event_suitability_optimal():
    # Mild 25°C, 0% rain, gentle 3 m/s wind
    score, label, reason = forecast_service.calculate_event_suitability(
        temp_max=25.0, max_pop=0.05, max_wind=3.0, condition="Clear sky"
    )
    assert score >= 80
    assert label == "Optimal"
    assert "low precipitation" in reason.lower() or "excellent" in reason.lower()


def test_calculate_event_suitability_rain_hazard():
    # Rainy with 85% probability
    score, label, reason = forecast_service.calculate_event_suitability(
        temp_max=28.0, max_pop=0.85, max_wind=6.0, condition="Moderate to heavy rain"
    )
    assert score <= 50
    assert "Unfavorable" in label or "Caution" in label
    assert "rain" in reason.lower()


def test_extract_day_parts_coverage():
    # Verify that morning, afternoon, evening, night are generated
    from app.schemas.weather import ForecastItem
    mock_items = [
        ForecastItem(time="2026-09-11 06:00:00", temperature=26.0, humidity=80, wind_speed=3.0, condition="Clear", pop=0.0),
        ForecastItem(time="2026-09-11 12:00:00", temperature=33.0, humidity=60, wind_speed=4.0, condition="Partly cloudy", pop=0.1),
        ForecastItem(time="2026-09-11 18:00:00", temperature=30.0, humidity=70, wind_speed=3.5, condition="Clouds", pop=0.2),
        ForecastItem(time="2026-09-11 23:00:00", temperature=27.0, humidity=82, wind_speed=2.5, condition="Clear", pop=0.0),
    ]
    parts = forecast_service._extract_day_parts(mock_items)
    assert len(parts) == 4
    part_keys = [p.part for p in parts]
    assert "morning" in part_keys
    assert "afternoon" in part_keys
    assert "evening" in part_keys
    assert "night" in part_keys


@pytest.mark.asyncio
async def test_nl_query_weekend_forecast():
    # Query "How is the weather this weekend?"
    req = ChatQueryRequest(
        message="How is the weather this weekend in Chennai?",
        city="Chennai",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert "weekend" in res.intent.lower() or "weekend" in res.answer.lower()
    assert res.weather_summary is not None
    assert "Saturday" in res.answer or "Sunday" in res.answer or "Weekend" in res.answer


@pytest.mark.asyncio
async def test_nl_query_outdoor_event_suitability():
    # Query "Will tomorrow be suitable for an outdoor event?"
    req = ChatQueryRequest(
        message="Will tomorrow be suitable for an outdoor event in Chennai?",
        city="Chennai",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert "outdoor event" in res.answer.lower() or "suitability" in res.answer.lower() or "feasibility" in res.answer.lower()
    assert res.recommendation is not None


@pytest.mark.asyncio
async def test_nl_query_running_morning_slot():
    # Query "Can I go running tomorrow morning?"
    req = ChatQueryRequest(
        message="Can I go running tomorrow morning in Chennai?",
        city="Chennai",
        language="en"
    )
    res = await ai_service.process_query(req)
    assert res.intent == "activity_advisory"
    assert res.risk_level is not None
    assert res.recommendation is not None and len(res.recommendation) > 10
    assert res.weather_summary["target_date"] == "tomorrow"
