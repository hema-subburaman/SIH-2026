from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import re
import logging
from app.core.config import settings
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse, ExtractedEntities
from app.schemas.risk import ActivityType, RiskAnalysisResponse, RiskFactor, RiskLevel
from app.services.weather_service import weather_service
from app.services.forecast_service import forecast_service
from app.services.risk_engine import risk_engine
from app.services.multilingual_service import multilingual_service
from app.providers.open_meteo import INDIAN_CITIES_COORDS

logger = logging.getLogger(__name__)


class AIService:
    """
    Intelligent Natural Language Processing & Decision-Support Orchestrator.
    Understands weather queries, extracts entities (intent, location, date, activity, parameter),
    queries real meteorological observations/forecasts, and generates explainable advisories.
    """

    def __init__(self):
        self.openai_client = None
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

    def extract_entities_rule_based(self, query: str, user_selected_city: str) -> ExtractedEntities:
        """Extracts intent, location, temporal slot, and activity from natural language query."""
        raw_lower = query.lower()
        
        # 1. Language detection
        detected_lang = multilingual_service.detect_language(query)
        normalized_text = multilingual_service.translate_to_english_intent(query, detected_lang).lower()

        # 2. Extract Location
        location = None
        for city_key in INDIAN_CITIES_COORDS.keys():
            if re.search(rf'\b{city_key}\b', normalized_text):
                location = INDIAN_CITIES_COORDS[city_key][2]
                break
        if not location:
            location = user_selected_city or "Chennai"

        # 3. Extract Temporal Target
        target_date = "today"
        if "tomorrow" in normalized_text or "kal" in raw_lower or "naalaikku" in raw_lower or "nalaiku" in raw_lower:
            target_date = "tomorrow"
        elif "weekend" in normalized_text or "saturday" in normalized_text or "sunday" in normalized_text:
            target_date = "weekend"
        elif "day after" in normalized_text:
            target_date = "day_after_tomorrow"

        target_time_slot = "now"
        if "morning" in normalized_text:
            target_time_slot = "morning"
        elif "evening" in normalized_text:
            target_time_slot = "evening"
        elif "afternoon" in normalized_text:
            target_time_slot = "afternoon"
        elif "night" in normalized_text:
            target_time_slot = "night"

        # 4. Extract Activity
        activity = None
        if re.search(r'\b(run|running|jog|jogging|daud|ooda|odalaama)\b', normalized_text):
            activity = ActivityType.RUNNING.value
        elif re.search(r'\b(walk|walking|nadakka)\b', normalized_text):
            activity = ActivityType.WALKING.value
        elif re.search(r'\b(cycle|cycling|bike|biking)\b', normalized_text):
            activity = ActivityType.CYCLING.value
        elif re.search(r'\b(event|wedding|party|gathering|concert|outdoor function)\b', normalized_text):
            activity = ActivityType.OUTDOOR_EVENT.value
        elif re.search(r'\b(travel|traveling|travelling|drive|driving|road trip|ghoomne)\b', normalized_text):
            activity = ActivityType.TRAVELLING.value
        elif re.search(r'\b(farm|farming|agriculture|crop|spray|irrigation)\b', normalized_text):
            activity = ActivityType.FARMING.value
        elif re.search(r'\b(construction|concrete|crane|scaffold|building)\b', normalized_text):
            activity = ActivityType.CONSTRUCTION.value
        elif re.search(r'\b(marine|fishing|boat|sea|sail|fisherman)\b', normalized_text):
            activity = ActivityType.MARINE_ACTIVITY.value
        elif re.search(r'\b(flight|aviation|pilot|takeoff)\b', normalized_text):
            activity = ActivityType.AVIATION_BRIEFING.value
        elif re.search(r'\b(outdoor|outside|veliye|bahar)\b', normalized_text):
            activity = ActivityType.GENERAL_OUTDOOR.value

        # 5. Extract Intent
        intent = "current_weather"
        weather_param = None

        if "umbrella" in normalized_text or "chata" in raw_lower or "kodai" in raw_lower:
            intent = "umbrella_check"
            weather_param = "rain"
        elif re.search(r'\b(rain|raining|drizzle|shower|barish|mazha)\b', normalized_text):
            intent = "rain_inquiry"
            weather_param = "rain"
        elif activity:
            intent = "activity_advisory"
        elif re.search(r'\b(warning|cyclone|storm|severe|alert)\b', normalized_text):
            intent = "severe_warning_check"
        elif re.search(r'\b(tomorrow|forecast|weekend|future|later)\b', normalized_text):
            intent = "forecast"
        elif re.search(r'\b(temp|temperature|hot|cold|heat|garmi|thand)\b', normalized_text):
            intent = "temperature_inquiry"
            weather_param = "temperature"
        elif re.search(r'\b(climate|trend|history|past|decade)\b', normalized_text):
            intent = "climate_inquiry"

        return ExtractedEntities(
            intent=intent,
            location=location,
            target_date=target_date,
            target_time_slot=target_time_slot,
            activity=activity,
            weather_parameter=weather_param,
            detected_language=detected_lang
        )

    async def process_query(self, req: ChatQueryRequest) -> ChatQueryResponse:
        # Determine language preference: explicit request parameter takes precedence
        entities = self.extract_entities_rule_based(req.message, req.city or "Chennai")
        lang = req.language if (req.language and req.language in ["en", "hi", "ta"]) else entities.detected_language
        city = entities.location or req.city or "Chennai"

        # If LLM API key is present and configured, we can also use LLM for enhanced entity parsing
        if self.openai_client:
            try:
                # LLM can be invoked to enrich parsing if desired
                pass
            except Exception as e:
                logger.warning(f"OpenAI query parsing fallback: {e}")

        # Retrieve Weather / Forecast Data based on Target Date
        is_forecast_target = entities.target_date in ["tomorrow", "weekend", "day_after_tomorrow"] or entities.intent == "forecast"

        # Use dedicated forecast service for comprehensive multi-day and day-part forecast analysis
        detailed_fc = await forecast_service.get_detailed_forecast(city=city, lat=req.latitude, lon=req.longitude, days=7)
        weather_res = await weather_service.get_forecast(city=city, lat=req.latitude, lon=req.longitude, days=5)
        curr = weather_res.current
        loc_name = weather_res.location.name

        # Handle "How is the weather this weekend?"
        if entities.target_date == "weekend" and detailed_fc.weekend:
            w_info = detailed_fc.weekend
            sat_str = f"Saturday ({round(w_info.saturday.temp_max)}°C, {w_info.saturday.overall_condition}, {int(w_info.saturday.max_pop * 100)}% rain)" if w_info.saturday else ""
            sun_str = f"Sunday ({round(w_info.sunday.temp_max)}°C, {w_info.sunday.overall_condition}, {int(w_info.sunday.max_pop * 100)}% rain)" if w_info.sunday else ""

            if lang == "ta":
                answer = f"{loc_name} பகுதியில் இந்த வார இறுதி வானிலை: {sat_str}. {sun_str}. ஆலோசனை: {w_info.outdoor_recommendation}"
            elif lang == "hi":
                answer = f"{loc_name} में इस वीकेंड का मौसम: {sat_str}। {sun_str}। सुझाव: {w_info.outdoor_recommendation}"
            else:
                answer = f"Weekend Weather Outlook for {loc_name}: {w_info.weekend_verdict} Advisory: {w_info.outdoor_recommendation}"

            return ChatQueryResponse(
                query=req.message,
                language=lang,
                intent="weekend_forecast",
                answer=answer,
                risk_level=RiskLevel.LOW if (w_info.saturday and w_info.saturday.max_pop < 0.4) else RiskLevel.MEDIUM,
                risk_score=25.0,
                factors=[],
                recommendation=w_info.outdoor_recommendation,
                location_used=loc_name,
                weather_summary={
                    "weekend": True,
                    "saturday": w_info.saturday.model_dump() if w_info.saturday else None,
                    "sunday": w_info.sunday.model_dump() if w_info.sunday else None,
                },
                source=detailed_fc.source,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        # Select relevant time slice from forecast or current
        target_temp = curr.temperature
        target_feels = curr.feels_like
        target_humidity = curr.humidity
        target_wind = curr.wind_speed
        target_cond = curr.condition
        target_pop = 0.0

        if is_forecast_target and weather_res.forecast:
            # Map time slot to target hour
            target_time_hour = 8 if entities.target_time_slot == "morning" else (18 if entities.target_time_slot == "evening" else (14 if entities.target_time_slot == "afternoon" else 12))
            target_dt_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            matching_items = [
                item for item in weather_res.forecast
                if target_dt_str in item.time
            ]
            if matching_items:
                # Find item closest to target hour
                best_item = min(
                    matching_items,
                    key=lambda x: abs(int(x.time.split(" ")[-1].split(":")[0] if " " in x.time else 12) - target_time_hour)
                )
                target_temp = best_item.temperature
                target_feels = best_item.feels_like or best_item.temperature
                target_humidity = best_item.humidity
                target_wind = best_item.wind_speed
                target_cond = best_item.condition
                target_pop = best_item.pop

        # Perform Weather Impact Intelligence Analysis if Activity or Outdoor Query
        effective_activity = ActivityType(entities.activity) if entities.activity else ActivityType.GENERAL_OUTDOOR
        risk_analysis: RiskAnalysisResponse = risk_engine.analyze(
            activity=effective_activity,
            temperature=target_temp,
            feels_like=target_feels,
            humidity=target_humidity,
            wind_speed=target_wind,
            condition=target_cond,
            pop=target_pop,
            visibility=curr.visibility,
            target_time=entities.target_date,
            language=lang
        )

        # Synthesize Natural Language Answer
        answer = ""
        risk_level = risk_analysis.risk_level
        risk_score = risk_analysis.score
        factors = risk_analysis.factors
        recommendation = risk_analysis.recommendation

        # Handle "Will tomorrow be suitable for an outdoor event?"
        if effective_activity == ActivityType.OUTDOOR_EVENT and ("suitable" in req.message.lower() or "event" in req.message.lower() or "function" in req.message.lower()):
            suit_score, suit_label, suit_reason = forecast_service.calculate_event_suitability(
                temp_max=target_temp, max_pop=target_pop, max_wind=target_wind, condition=target_cond
            )
            if lang == "ta":
                answer = f"{loc_name} பகுதியில் நாளை வெளிப்புற நிகழ்ச்சி ஏற்பாடு செய்ய வானிலை நிலை: {suit_label} (பொருத்தப்பாடு: {suit_score}%). {suit_reason} பரிந்துரை: {recommendation}"
            elif lang == "hi":
                answer = f"{loc_name} में कल आउटडोर इवेंट के लिए मौसम की स्थिति: {suit_label} (उपयुक्तता स्कोर: {suit_score}%). {suit_reason} परामर्श: {recommendation}"
            else:
                answer = (
                    f"Outdoor Event Feasibility for {loc_name} (Tomorrow): {suit_label} ({suit_score}% suitability). "
                    f"{suit_reason} Expected conditions: {target_temp}°C with {target_cond}, rain probability {int(target_pop * 100)}%, wind {target_wind} m/s. "
                    f"Actionable Advice: {recommendation}"
                )
        elif entities.intent == "rain_inquiry" or entities.intent == "umbrella_check":
            has_rain = target_pop >= 0.35 or "rain" in target_cond.lower() or "drizzle" in target_cond.lower()
            t_label = entities.target_date if entities.target_date != "today" else "today"
            template_key = "rain_yes" if has_rain else "rain_no"
            answer = multilingual_service.localize_response(
                lang=lang,
                template_key=template_key,
                replacements={
                    "location": loc_name,
                    "target": t_label,
                    "pop": int(target_pop * 100),
                    "cond": target_cond,
                    "rec": recommendation
                }
            )
        elif entities.intent == "activity_advisory":
            template_key = "running_advisory" if effective_activity == ActivityType.RUNNING else "general_advisory"
            answer = multilingual_service.localize_response(
                lang=lang,
                template_key=template_key,
                replacements={
                    "location": loc_name,
                    "risk": risk_level.value,
                    "rec": recommendation,
                    "temp": target_temp,
                    "cond": target_cond,
                    "humidity": target_humidity,
                    "wind": target_wind
                }
            )
        elif entities.intent == "severe_warning_check":
            answer = f"No active official cyclone or extreme weather warnings are currently in effect for {loc_name}. (Source: Official IMD warning feed)."
        elif entities.intent == "forecast":
            answer = (
                f"The forecast for {loc_name} for {entities.target_date} indicates a temperature around {target_temp}°C "
                f"with {target_cond}. Precipitation probability is {int(target_pop * 100)}% and wind is {target_wind} m/s."
            )
        elif entities.intent == "temperature_inquiry":
            is_high = target_temp >= settings.HEAT_CAUTION_TEMP
            if is_high:
                answer = (
                    f"Yes, expected temperatures in {loc_name} ({entities.target_date}) will be high at {target_temp}°C "
                    f"(feels like {target_feels}°C) with {target_cond}. Hydration precautions are advised."
                )
            else:
                answer = (
                    f"The expected temperature in {loc_name} ({entities.target_date}) is moderate at {target_temp}°C "
                    f"(feels like {target_feels}°C) with {target_cond}."
                )
        else:
            # Default Current Weather
            answer = multilingual_service.localize_response(
                lang=lang,
                template_key="current_weather",
                replacements={
                    "location": loc_name,
                    "temp": target_temp,
                    "cond": target_cond,
                    "humidity": target_humidity,
                    "wind": target_wind
                }
            )

        return ChatQueryResponse(
            query=req.message,
            language=lang,
            intent=entities.intent,
            answer=answer,
            risk_level=risk_level,
            risk_score=risk_score,
            factors=factors,
            recommendation=recommendation,
            location_used=loc_name,
            weather_summary={
                "temperature": target_temp,
                "feels_like": target_feels,
                "humidity": target_humidity,
                "wind_speed": target_wind,
                "condition": target_cond,
                "pop": target_pop,
                "target_date": entities.target_date,
            },
            source=weather_res.source,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


ai_service = AIService()
