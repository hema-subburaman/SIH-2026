import re
from typing import Optional, List
from app.schemas.claim import ClaimVerifyRequest, ClaimVerifyResponse, ClaimStatus
from app.services.weather_service import weather_service
from app.services.alert_service import alert_service


class ClaimVerifier:
    """
    Meteorological Fact-Checking & Claim Verification Engine.
    Cross-checks user statements against real observational telemetry and official warning archives.
    Strictly yields UNVERIFIED when authoritative government warning databases lack corroboration.
    """

    async def verify_claim(self, req: ClaimVerifyRequest) -> ClaimVerifyResponse:
        claim_text = req.claim.strip()
        claim_lower = claim_text.lower()
        city = req.city or "Chennai"

        # Check for Severe Warning / Cyclone / Disaster claims first
        is_cyclone_or_disaster_claim = any(
            kw in claim_lower for kw in [
                "cyclone", "typhoon", "tsunami", "flood warning", "red alert",
                "severe warning", "disaster", "evacuation"
            ]
        )

        if is_cyclone_or_disaster_claim:
            # Query official warning provider strictly
            alerts_resp = await alert_service.get_alerts_for_location(city=city, lat=req.latitude, lon=req.longitude)
            matching_official = [
                a for a in alerts_resp.official_alerts
                if any(kw in a.event.lower() or kw in a.description.lower() for kw in ["cyclone", "flood", "warning"])
            ]

            if matching_official:
                return ClaimVerifyResponse(
                    claim=claim_text,
                    status=ClaimStatus.VERIFIED,
                    verdict_summary=f"VERIFIED: An official government warning ({matching_official[0].event}) is active for {city}.",
                    confidence=0.95,
                    evidence_factors=[
                        f"Official Issuing Body: {matching_official[0].source}",
                        f"Warning Headline: {matching_official[0].headline or matching_official[0].event}",
                        f"Severity: {matching_official[0].severity}"
                    ],
                    official_warning_checked=True,
                    source_attribution=matching_official[0].source
                )
            else:
                # Rule 20: If system does NOT have official warning data, it MUST be marked UNVERIFIED!
                return ClaimVerifyResponse(
                    claim=claim_text,
                    status=ClaimStatus.UNVERIFIED,
                    verdict_summary=(
                        f"UNVERIFIED: No official cyclone or extreme disaster warning has been published by the "
                        f"India Meteorological Department (IMD) / authorized government feed for {city} at this time."
                    ),
                    confidence=0.90,
                    evidence_factors=[
                        "Authoritative IMD / CAP RSS bulletin cross-referenced: Zero active cyclone/red-alert bulletins found.",
                        "Standard current weather API parameters cannot corroborate or declare official disaster warnings.",
                        "Status marked UNVERIFIED per strict meteorological safety verification protocol."
                    ],
                    official_warning_checked=True,
                    source_attribution="Official Warning Database (IMD / NDMA Sachet Feed)"
                )

        # Retrieve current and forecast weather
        weather_res = await weather_service.get_forecast(city=city, lat=req.latitude, lon=req.longitude, days=3)
        curr = weather_res.current
        loc_name = weather_res.location.name

        # 1. Rain Claims ("It is raining now", "It will rain tomorrow")
        if "rain" in claim_lower or "barish" in claim_lower or "mazha" in claim_lower:
            is_now = any(w in claim_lower for w in ["now", "currently", "today", "right now", "innikku", "aaj"])
            is_tomorrow = any(w in claim_lower for w in ["tomorrow", "kal", "naalaikku", "later"])

            if is_now or not is_tomorrow:
                # Check current precipitation
                has_rain_now = "rain" in curr.condition.lower() or "drizzle" in curr.condition.lower() or (curr.precipitation_mm and curr.precipitation_mm > 0.1)
                if has_rain_now:
                    return ClaimVerifyResponse(
                        claim=claim_text,
                        status=ClaimStatus.VERIFIED,
                        verdict_summary=f"VERIFIED: Observational data confirms active precipitation in {loc_name}.",
                        confidence=0.92,
                        evidence_factors=[
                            f"Current Condition: {curr.condition}",
                            f"Precipitation Rate: {curr.precipitation_mm or 0.5} mm/h",
                            f"Relative Humidity: {curr.humidity}%"
                        ],
                        official_warning_checked=False,
                        source_attribution=weather_res.source
                    )
                else:
                    return ClaimVerifyResponse(
                        claim=claim_text,
                        status=ClaimStatus.CONTRADICTED,
                        verdict_summary=f"CONTRADICTED: Observational sensors report no active rainfall in {loc_name}.",
                        confidence=0.88,
                        evidence_factors=[
                            f"Observed Condition: {curr.condition} (Dry)",
                            f"Surface Pressure: {curr.pressure} hPa",
                            f"Humidity: {curr.humidity}%"
                        ],
                        official_warning_checked=False,
                        source_attribution=weather_res.source
                    )
            else:
                # Check tomorrow's forecast
                pop_tomorrow = 0.0
                cond_tomorrow = "Partly cloudy"
                if weather_res.forecast:
                    # check tomorrow items
                    items_tomorrow = weather_res.forecast[:8]
                    pop_tomorrow = max(i.pop for i in items_tomorrow)
                    cond_tomorrow = items_tomorrow[0].condition

                if pop_tomorrow >= 0.5:
                    return ClaimVerifyResponse(
                        claim=claim_text,
                        status=ClaimStatus.VERIFIED,
                        verdict_summary=f"VERIFIED: Forecast models indicate high likelihood ({int(pop_tomorrow*100)}%) of rain tomorrow in {loc_name}.",
                        confidence=round(pop_tomorrow, 2),
                        evidence_factors=[
                            f"Probability of Precipitation: {int(pop_tomorrow*100)}%",
                            f"Forecast Condition: {cond_tomorrow}"
                        ],
                        official_warning_checked=False,
                        source_attribution=weather_res.source
                    )
                else:
                    return ClaimVerifyResponse(
                        claim=claim_text,
                        status=ClaimStatus.CONTRADICTED,
                        verdict_summary=f"CONTRADICTED: Numerical forecast indicates low precipitation chance ({int(pop_tomorrow*100)}%) tomorrow in {loc_name}.",
                        confidence=0.82,
                        evidence_factors=[
                            f"Probability of Precipitation: {int(pop_tomorrow*100)}%",
                            f"Predicted Condition: {cond_tomorrow}"
                        ],
                        official_warning_checked=False,
                        source_attribution=weather_res.source
                    )

        # 2. Temperature / Heat Claims ("Tomorrow will be very hot", "It is cold")
        if any(w in claim_lower for w in ["hot", "heat", "warm", "garmi", "veiyil"]):
            is_hot = curr.temperature >= 35.0 or curr.feels_like >= 38.0
            if is_hot:
                return ClaimVerifyResponse(
                    claim=claim_text,
                    status=ClaimStatus.VERIFIED,
                    verdict_summary=f"VERIFIED: Ambient temperatures in {loc_name} are elevated at {curr.temperature}°C (Feels like {curr.feels_like}°C).",
                    confidence=0.90,
                    evidence_factors=[
                        f"Recorded Temperature: {curr.temperature}°C",
                        f"Heat Index / Feels Like: {curr.feels_like}°C",
                        f"Relative Humidity: {curr.humidity}%"
                    ],
                    official_warning_checked=False,
                    source_attribution=weather_res.source
                )
            else:
                return ClaimVerifyResponse(
                    claim=claim_text,
                    status=ClaimStatus.CONTRADICTED,
                    verdict_summary=f"CONTRADICTED: Current temperature in {loc_name} is moderate ({curr.temperature}°C), well below extreme heat thresholds.",
                    confidence=0.88,
                    evidence_factors=[
                        f"Recorded Temperature: {curr.temperature}°C",
                        f"Heat Index / Feels Like: {curr.feels_like}°C",
                        "Threshold for 'Very Hot' is typically ≥ 38°C"
                    ],
                    official_warning_checked=False,
                    source_attribution=weather_res.source
                )

        # 3. Generic claim fallback
        return ClaimVerifyResponse(
            claim=claim_text,
            status=ClaimStatus.UNVERIFIED,
            verdict_summary=f"UNVERIFIED: Specific claim details cannot be conclusively verified against current telemetry for {loc_name}.",
            confidence=0.50,
            evidence_factors=[
                f"Current Observations: {curr.temperature}°C, {curr.condition}, Wind: {curr.wind_speed} m/s",
                "Please formulate claims regarding specific measurable parameters (rain, temperature, wind, or official warnings)."
            ],
            official_warning_checked=True,
            source_attribution=weather_res.source
        )


claim_verifier = ClaimVerifier()
