from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DISCLAIMER_NOTICE = "WeatherGPT decision-support threshold (algorithmic guidance, not an official government directive)"


class DomainAdvisoryResponse(BaseModel):
    """Structured response for use-case specialized meteorological decision support."""
    persona: str = Field(..., description="Target persona: agriculture, marine, travel, construction, aviation, events, general")
    city: str
    decision: str = Field(..., description="PROCEED, CAUTION, HIGH_RISK, SUSPEND")
    confidence: str = Field(..., description="High, Moderate, Low")
    suitability_score: int = Field(..., ge=0, le=100, description="0-100 suitability score")
    summary: str
    actionable_recommendations: List[str] = Field(default_factory=list)
    critical_factors: List[Dict[str, Any]] = Field(default_factory=list)
    decision_threshold_label: str = DISCLAIMER_NOTICE
    official_warning_separate: bool = True
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class AdvisoryEngine:
    """
    Multi-Sector Meteorological Decision-Support Advisory Engine.
    Evaluates meteorological factors across 7 specialized use cases with explicit threshold transparency.
    """

    @staticmethod
    def evaluate_agriculture(
        temp: float, humidity: int, wind_speed: float, precip_mm: float, pop: float = 0.0
    ) -> DomainAdvisoryResponse:
        """Advisory for farming, spraying, harvesting, and irrigation."""
        factors = []
        score = 100
        recs = []
        decision = "PROCEED"

        # Spraying factor: Wind speed
        if wind_speed > 5.5:
            score -= 30
            factors.append({"factor": "Wind Speed", "value": f"{wind_speed} m/s", "impact": "High chemical pesticide drift risk"})
            recs.append("Postpone foliar pesticide or herbicide spraying due to strong wind drift.")
        elif wind_speed < 1.0:
            recs.append("Low wind favors controlled field spraying.")

        # Rain factor: Irrigation / Harvest
        if precip_mm > 5.0 or pop >= 0.60:
            score -= 40
            factors.append({"factor": "Rainfall Risk", "value": f"{precip_mm} mm (prob: {int(pop*100)}%)", "impact": "Waterlogging / wash-off risk"})
            recs.append("Suspend manual irrigation to prevent waterlogging. Delay open-field harvesting or threshing.")
        elif precip_mm < 0.5 and pop < 0.20:
            recs.append("Dry conditions: Safe for harvesting, tilling, and grain drying.")

        # Heat stress
        if temp >= 38.0:
            score -= 25
            factors.append({"factor": "High Temperature", "value": f"{temp}°C", "impact": "Evapotranspiration stress"})
            recs.append("Provide supplemental evening irrigation to mitigate high evapotranspiration stress on crops.")

        # Humidity & Fungal disease
        if humidity > 85 and temp > 25.0:
            factors.append({"factor": "High Humidity", "value": f"{humidity}%", "impact": "Elevated fungal spore propagation"})
            recs.append("Inspect crop foliage for blast or blight fungal pathogens favored by sustained high humidity.")

        score = max(5, min(100, score))
        if score < 40:
            decision = "SUSPEND"
        elif score < 70:
            decision = "CAUTION"

        summary = f"Agricultural suitability score: {score}/100 ({decision}). " + (" ".join(recs[:2]) if recs else "Favorable conditions for farming operations.")

        return DomainAdvisoryResponse(
            persona="agriculture",
            city="",
            decision=decision,
            confidence="High",
            suitability_score=score,
            summary=summary,
            actionable_recommendations=recs,
            critical_factors=factors,
        )

    @staticmethod
    def evaluate_marine(
        wind_speed: float, precip_mm: float, condition: str = ""
    ) -> DomainAdvisoryResponse:
        """Advisory for fishermen and coastal marine activities."""
        factors = []
        score = 100
        recs = []
        decision = "PROCEED"

        # Wind threshold: >= 11 m/s (~40 km/h) is rough sea
        if wind_speed >= 12.0:
            score -= 60
            decision = "SUSPEND"
            factors.append({"factor": "Sustained Gale Wind", "value": f"{wind_speed} m/s (~{round(wind_speed*3.6)} km/h)", "impact": "Extremely rough sea state"})
            recs.append("Fishermen are strongly advised NOT to venture into deep sea or coastal waters.")
        elif wind_speed >= 8.5:
            score -= 30
            decision = "CAUTION"
            factors.append({"factor": "Moderate Breeze", "value": f"{wind_speed} m/s", "impact": "Moderate swell / choppy waters"})
            recs.append("Small craft vessels should exercise heightened caution near harbors.")

        # Squall / Thunderstorm
        if "thunder" in condition.lower() or "storm" in condition.lower():
            score = min(score, 20)
            decision = "SUSPEND"
            factors.append({"factor": "Convective Squall", "value": condition, "impact": "Sudden localized wind shear & high waves"})
            recs.append("Squally weather detected over marine zone. Return to harbor immediately.")

        score = max(5, min(100, score))
        summary = f"Marine operations verdict: {decision} (Suitability: {score}/100). " + (" ".join(recs[:2]) if recs else "Sea conditions normal.")

        return DomainAdvisoryResponse(
            persona="marine",
            city="",
            decision=decision,
            confidence="High",
            suitability_score=score,
            summary=summary,
            actionable_recommendations=recs,
            critical_factors=factors,
        )

    @staticmethod
    def evaluate_travel(
        precip_mm: float, wind_speed: float, visibility_m: Optional[float] = 10000.0, condition: str = ""
    ) -> DomainAdvisoryResponse:
        """Advisory for highway, rail, and urban travel."""
        factors = []
        score = 100
        recs = []
        decision = "PROCEED"

        vis = visibility_m if visibility_m is not None else 10000.0
        if vis < 1000.0:
            score -= 40
            decision = "CAUTION"
            factors.append({"factor": "Dense Fog / Low Visibility", "value": f"{int(vis)} m", "impact": "Hazardous road travel / transit delays"})
            recs.append("Dense fog alert: Reduce highway vehicle speed and use low-beam fog headlights.")
        
        if precip_mm > 10.0 or "heavy rain" in condition.lower():
            score -= 35
            decision = "CAUTION"
            factors.append({"factor": "Heavy Rain", "value": f"{precip_mm} mm", "impact": "Road waterlogging and hydroplaning"})
            recs.append("Expect highway waterlogging and reduced tire traction. Add 30-45 minutes travel buffer.")

        if wind_speed >= 14.0:
            score -= 30
            factors.append({"factor": "High Crosswinds", "value": f"{wind_speed} m/s", "impact": "Stability hazard for two-wheelers and high-profile buses"})
            recs.append("Two-wheelers and high-sided trucks should exercise caution on elevated flyovers and open highways.")

        score = max(5, min(100, score))
        if score < 40:
            decision = "HIGH_RISK"

        summary = f"Travel suitability: {score}/100 ({decision}). " + (" ".join(recs[:2]) if recs else "Clear journey conditions across routes.")

        return DomainAdvisoryResponse(
            persona="travel",
            city="",
            decision=decision,
            confidence="High",
            suitability_score=score,
            summary=summary,
            actionable_recommendations=recs,
            critical_factors=factors,
        )

    @staticmethod
    def evaluate_construction(
        temp: float, wind_speed: float, precip_mm: float, condition: str = ""
    ) -> DomainAdvisoryResponse:
        """Advisory for construction worksites and high-elevation operations."""
        factors = []
        score = 100
        recs = []
        decision = "PROCEED"

        # High wind crane safety (> 10 m/s ~ 36 km/h)
        if wind_speed >= 10.0:
            score -= 50
            decision = "SUSPEND"
            factors.append({"factor": "Tower Crane Wind Limit Exceeded", "value": f"{wind_speed} m/s", "impact": "Crane load swing & scaffolding hazard"})
            recs.append("Halt tower crane lifting operations and secure loose scaffolding materials immediately.")

        # Extreme heat stress
        if temp >= 40.0:
            score -= 35
            decision = "CAUTION"
            factors.append({"factor": "Severe Heat Stress", "value": f"{temp}°C", "impact": "Worker heat exhaustion / heatstroke"})
            recs.append("Mandate 15-minute shaded hydration breaks every hour between 12:00 PM and 3:30 PM.")

        # Rain concrete impact
        if precip_mm > 2.0:
            score -= 30
            factors.append({"factor": "Rainfall", "value": f"{precip_mm} mm", "impact": "Adverse setting of fresh concrete"})
            recs.append("Delay external concrete slab pouring and protect fresh plastering from rainfall.")

        score = max(5, min(100, score))
        summary = f"Construction safety index: {score}/100 ({decision}). " + (" ".join(recs[:2]) if recs else "Favorable conditions for site work.")

        return DomainAdvisoryResponse(
            persona="construction",
            city="",
            decision=decision,
            confidence="High",
            suitability_score=score,
            summary=summary,
            actionable_recommendations=recs,
            critical_factors=factors,
        )

    @staticmethod
    def evaluate_aviation(
        wind_speed: float, visibility_m: Optional[float] = 10000.0, cape: Optional[float] = None, condition: str = ""
    ) -> DomainAdvisoryResponse:
        """Advisory briefing for general aviation, flight schools, and drone UAV missions."""
        factors = []
        score = 100
        recs = []
        decision = "PROCEED"

        vis = visibility_m if visibility_m is not None else 10000.0
        if vis < 3000.0:
            score -= 50
            decision = "CAUTION"
            factors.append({"factor": "VFR Minimums Compromised", "value": f"{int(vis)} m", "impact": "Marginal VFR / IFR requirement"})
            recs.append("Visual Flight Rules (VFR) flight operations restricted. Instrument rating required.")

        if wind_speed >= 10.0:
            score -= 35
            factors.append({"factor": "Surface Crosswind", "value": f"{wind_speed} m/s", "impact": "Runway crosswind limit / drone stability"})
            recs.append("Drone UAV operations should be suspended if manufacturer wind threshold (<10 m/s) is exceeded.")

        if cape and cape > 1500:
            score -= 30
            factors.append({"factor": "Convective Available Potential Energy (CAPE)", "value": f"{int(cape)} J/kg", "impact": "Severe updrafts & thunderstorm formation"})
            recs.append("High thermodynamic instability (CAPE > 1500 J/kg). Expect sudden towering cumulonimbus development.")

        score = max(5, min(100, score))
        if score < 40:
            decision = "SUSPEND"

        summary = f"Aviation briefing verdict: {decision} (Score: {score}/100). " + (" ".join(recs[:2]) if recs else "Favorable VFR flight conditions.")

        return DomainAdvisoryResponse(
            persona="aviation",
            city="",
            decision=decision,
            confidence="High",
            suitability_score=score,
            summary=summary,
            actionable_recommendations=recs,
            critical_factors=factors,
        )

    @classmethod
    def evaluate(
        cls,
        persona: str,
        city: str,
        temp: float,
        humidity: int,
        wind_speed: float,
        precip_mm: float = 0.0,
        pop: float = 0.0,
        visibility: Optional[float] = 10000.0,
        cape: Optional[float] = None,
        condition: str = "Clear",
    ) -> DomainAdvisoryResponse:
        """Routes evaluation to the matching domain handler with standardized output."""
        p = persona.lower().strip()
        if p in ("farmer", "farming", "agriculture"):
            res = cls.evaluate_agriculture(temp, humidity, wind_speed, precip_mm, pop)
        elif p in ("fisherman", "fishing", "marine"):
            res = cls.evaluate_marine(wind_speed, precip_mm, condition)
        elif p in ("traveler", "travel", "journey", "transport"):
            res = cls.evaluate_travel(precip_mm, wind_speed, visibility, condition)
        elif p in ("construction", "builder", "contractor"):
            res = cls.evaluate_construction(temp, wind_speed, precip_mm, condition)
        elif p in ("aviation", "pilot", "drone"):
            res = cls.evaluate_aviation(wind_speed, visibility, cape, condition)
        else:
            # General outdoor
            score = 90
            recs = ["Normal outdoor activity conditions."]
            if precip_mm > 1.0 or pop >= 0.5:
                score -= 30
                recs = ["Carry an umbrella or light rain gear."]
            if temp > 36.0:
                score -= 20
                recs.append("Stay well hydrated during peak afternoon sunshine.")
            res = DomainAdvisoryResponse(
                persona="general",
                city=city,
                decision="PROCEED" if score >= 70 else "CAUTION",
                confidence="High",
                suitability_score=score,
                summary=f"General outdoor score: {score}/100.",
                actionable_recommendations=recs,
            )

        res.city = city
        return res


advisory_engine = AdvisoryEngine()
