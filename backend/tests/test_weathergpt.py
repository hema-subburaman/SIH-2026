import pytest
from app.schemas.risk import ActivityType, RiskLevel
from app.services.risk_engine import risk_engine
from app.services.multilingual_service import multilingual_service
from app.services.ai_service import ai_service
from app.schemas.claim import ClaimVerifyRequest, ClaimStatus
from app.services.claim_verifier import claim_verifier


def test_heat_index_calculation():
    # 35°C with 70% humidity should produce dangerous heat index
    hi = risk_engine.calculate_heat_index(35.0, 70)
    assert hi > 45.0, f"Expected high heat index, got {hi}"


def test_risk_engine_running_high_heat():
    analysis = risk_engine.analyze(
        activity=ActivityType.RUNNING,
        temperature=36.0,
        humidity=75,
        wind_speed=3.0,
        condition="Hot and Humid",
        pop=0.1
    )
    assert analysis.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]
    assert len(analysis.factors) > 0
    assert "running" in analysis.recommendation.lower() or "postpone" in analysis.recommendation.lower() or "drink" in analysis.recommendation.lower()


def test_risk_engine_thunderstorm_hazard():
    analysis = risk_engine.analyze(
        activity=ActivityType.GENERAL_OUTDOOR,
        temperature=28.0,
        humidity=80,
        wind_speed=8.0,
        condition="Thunderstorm with Heavy Rain",
        pop=0.9
    )
    assert analysis.risk_level == RiskLevel.HIGH
    assert any("Thunderstorm" in f.parameter for f in analysis.factors)
    assert "shelter" in analysis.recommendation.lower() or "lightning" in analysis.explanation.lower()


def test_multilingual_detection_and_translation():
    # Tamil
    ta_query = "Naalaikku mazha varuma?"
    detected_ta = multilingual_service.detect_language(ta_query)
    assert detected_ta == "ta"

    # Hindi
    hi_query = "Kya kal barish hogi?"
    detected_hi = multilingual_service.detect_language(hi_query)
    assert detected_hi == "hi"

    # English
    en_query = "Will it rain tomorrow in Chennai?"
    detected_en = multilingual_service.detect_language(en_query)
    assert detected_en == "en"


def test_ai_entity_extraction():
    entities = ai_service.extract_entities_rule_based(
        query="Can I go for a run tomorrow evening in Delhi?",
        user_selected_city="Chennai"
    )
    assert entities.intent == "activity_advisory"
    assert entities.activity == "running"
    assert entities.location == "Delhi"
    assert entities.target_date == "tomorrow"
    assert entities.target_time_slot == "evening"


@pytest.mark.asyncio
async def test_claim_verification_cyclone_unverified():
    # A claim about cyclone without official IMD warning should be UNVERIFIED per SIH Rule 20
    req = ClaimVerifyRequest(
        claim="There is a severe cyclone warning in Mumbai right now",
        city="Mumbai"
    )
    res = await claim_verifier.verify_claim(req)
    assert res.status == ClaimStatus.UNVERIFIED
    assert res.official_warning_checked is True
    assert "UNVERIFIED" in res.verdict_summary
