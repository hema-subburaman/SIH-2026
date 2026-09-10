from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import json
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
    Features an optional LLM layer with strict JSON schema validation and zero-dependency rule-based fallback.
    """

    def __init__(self):
        self.openai_client = None
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized for enhanced query understanding.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

    async def extract_entities_llm(self, query: str, user_selected_city: str) -> Optional[ExtractedEntities]:
        """
        Extracts structured entities using LLM when configured.
        Strictly produces JSON entities only; NEVER fabricates weather data.
        Falls back to None if parsing or validation fails.
        """
        if not self.openai_client:
            return None

        prompt = (
            "You are a strict meteorological Natural Language Understanding (NLU) component for WeatherGPT.\n"
            "Your ONLY task is to parse the user's natural language weather inquiry and extract entities into JSON.\n"
            "CRITICAL: Do NOT invent, generate, or predict weather data. Only extract intent and context.\n"
            "Return JSON matching this exact structure:\n"
            "{\n"
            '  "intent": "current_weather" | "forecast" | "weekend_forecast" | "rain_inquiry" | "umbrella_check" | "activity_advisory" | "temperature_inquiry" | "severe_warning_check" | "climate_inquiry",\n'
            '  "location": string or null,\n'
            '  "target_date": "today" | "tomorrow" | "day_after_tomorrow" | "weekend" | "saturday" | "sunday",\n'
            '  "target_time_slot": "now" | "morning" | "afternoon" | "evening" | "night",\n'
            '  "activity": "running" | "walking" | "cycling" | "outdoor_event" | "travelling" | "farming" | "construction" | "marine_activity" | "aviation_briefing" | "general_outdoor" | null,\n'
            '  "weather_parameter": "rain" | "temperature" | "wind" | "humidity" | null,\n'
            '  "language": "en" | "hi" | "ta"\n'
            "}\n"
            f"User Query: {query}\n"
            f"User Active City: {user_selected_city}\n"
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a weather NLU entity parser. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=250,
                timeout=5.0
            )
            raw_json = response.choices[0].message.content
            parsed = json.loads(raw_json)

            # Validate activity
            raw_act = parsed.get("activity")
            valid_act = None
            if raw_act:
                valid_acts = [a.value for a in ActivityType]
                if raw_act in valid_acts:
                    valid_act = raw_act
                else:
                    valid_act = ActivityType.GENERAL_OUTDOOR.value

            return ExtractedEntities(
                intent=parsed.get("intent", "current_weather"),
                location=parsed.get("location") or user_selected_city,
                target_date=parsed.get("target_date", "today"),
                target_time_slot=parsed.get("target_time_slot", "now"),
                activity=valid_act,
                weather_parameter=parsed.get("weather_parameter"),
                detected_language=parsed.get("language", "en"),
                is_llm_enhanced=True
            )
        except Exception as e:
            logger.warning(f"LLM entity extraction failed or timed out: {e}. Falling back to rule-based NLU.")
            return None

    def extract_entities_rule_based(self, query: str, user_selected_city: str) -> ExtractedEntities:
        """Extracts intent, location, temporal slot, and activity from natural language query using rule-based NLU."""
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
        if "day after" in normalized_text or "parson" in raw_lower or "marunaal" in raw_lower:
            target_date = "day_after_tomorrow"
        elif "tomorrow" in normalized_text or "kal" in raw_lower or "naalaikku" in raw_lower or "nalaiku" in raw_lower or "naalai" in raw_lower:
            target_date = "tomorrow"
        elif "saturday" in normalized_text or "shaniwar" in raw_lower or "sanikizhamai" in raw_lower:
            target_date = "saturday"
        elif "sunday" in normalized_text or "raviwar" in raw_lower or "gnyayiru" in raw_lower:
            target_date = "sunday"
        elif "weekend" in normalized_text or "vaara iruthi" in raw_lower or "saptahant" in raw_lower:
            target_date = "weekend"

        target_time_slot = "now"
        if "morning" in normalized_text or "subah" in raw_lower or "kaalai" in raw_lower:
            target_time_slot = "morning"
        elif "afternoon" in normalized_text or "dopahar" in raw_lower or "madhiyam" in raw_lower:
            target_time_slot = "afternoon"
        elif "evening" in normalized_text or "shaam" in raw_lower or "maalai" in raw_lower or "sayangalam" in raw_lower:
            target_time_slot = "evening"
        elif "night" in normalized_text or "raat" in raw_lower or "iravu" in raw_lower:
            target_time_slot = "night"

        # 4. Extract Activity
        activity = None
        if re.search(r'\b(run|running|jog|jogging|daud|doud|ooda|odalaama)\b', normalized_text):
            activity = ActivityType.RUNNING.value
        elif re.search(r'\b(walk|walking|nadakka|tahalne)\b', normalized_text):
            activity = ActivityType.WALKING.value
        elif re.search(r'\b(cycle|cycling|bike|biking)\b', normalized_text):
            activity = ActivityType.CYCLING.value
        elif re.search(r'\b(event|wedding|party|gathering|concert|function|karyakram|nigarzhchi)\b', normalized_text):
            activity = ActivityType.OUTDOOR_EVENT.value
        elif re.search(r'\b(travel|traveling|travelling|drive|driving|trip|ghoomne|safar|yatra|payanam)\b', normalized_text):
            activity = ActivityType.TRAVELLING.value
        elif re.search(r'\b(farm|farming|agriculture|crop|crops|spray|spraying|irrigation|kheti|chhidkav|vivasaayam|thelikkalama)\b', normalized_text):
            activity = ActivityType.FARMING.value
        elif re.search(r'\b(construction|concrete|crane|scaffold|building|cement)\b', normalized_text):
            activity = ActivityType.CONSTRUCTION.value
        elif re.search(r'\b(marine|fishing|boat|sea|sail|fisherman|fishermen|machli|meen|meenpidikka|kadal)\b', normalized_text):
            activity = ActivityType.MARINE_ACTIVITY.value
        elif re.search(r'\b(flight|aviation|pilot|takeoff)\b', normalized_text):
            activity = ActivityType.AVIATION_BRIEFING.value
        elif re.search(r'\b(outdoor|outside|veliye|veliya|bahar)\b', normalized_text):
            activity = ActivityType.GENERAL_OUTDOOR.value

        # 5. Extract Intent
        intent = "current_weather"
        weather_param = None

        if "umbrella" in normalized_text or "chata" in raw_lower or "kodai" in raw_lower:
            intent = "umbrella_check"
            weather_param = "rain"
        elif re.search(r'\b(rain|raining|drizzle|shower|barish|mazha|mazhai)\b', normalized_text):
            intent = "rain_inquiry"
            weather_param = "rain"
        elif activity:
            intent = "activity_advisory"
        elif re.search(r'\b(warning|cyclone|storm|severe|alert|tsunami)\b', normalized_text):
            intent = "severe_warning_check"
        elif target_date in ["weekend", "saturday", "sunday"]:
            intent = "weekend_forecast"
        elif target_date in ["tomorrow", "day_after_tomorrow"] or re.search(r'\b(forecast|future|later)\b', normalized_text):
            intent = "forecast"
        elif re.search(r'\b(temp|temperature|hot|cold|heat|garmi|thand|veiyil|kulir)\b', normalized_text):
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
            detected_language=detected_lang,
            is_llm_enhanced=False
        )

    def _calculate_target_date_string(self, target_date: str) -> str:
        """Calculates precise target ISO date YYYY-MM-DD from semantic target."""
        now = datetime.now()
        if target_date == "tomorrow":
            return (now + timedelta(days=1)).strftime("%Y-%m-%d")
        elif target_date == "day_after_tomorrow":
            return (now + timedelta(days=2)).strftime("%Y-%m-%d")
        elif target_date in ["weekend", "saturday"]:
            # Days until Saturday (weekday 5)
            days_ahead = (5 - now.weekday()) % 7
            if days_ahead == 0 and target_date == "weekend":
                days_ahead = 0
            elif days_ahead == 0:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif target_date == "sunday":
            # Days until Sunday (weekday 6)
            days_ahead = (6 - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        return now.strftime("%Y-%m-%d")

    async def process_query(self, req: ChatQueryRequest) -> ChatQueryResponse:
        # 1. Entity Extraction: LLM when configured, fallback to rule-based NLU
        entities = None
        if self.openai_client:
            entities = await self.extract_entities_llm(req.message, req.city or "Chennai")

        if not entities:
            entities = self.extract_entities_rule_based(req.message, req.city or "Chennai")

        lang = req.language if (req.language and req.language in ["en", "hi", "ta"]) else entities.detected_language
        city = entities.location or req.city or "Chennai"

        # 2. Determine whether this is a forecast target
        is_forecast_target = (
            entities.target_date in ["tomorrow", "weekend", "day_after_tomorrow", "saturday", "sunday"]
            or entities.intent in ["forecast", "weekend_forecast"]
        )

        # 3. Retrieve Real Meteorological Data from Providers
        detailed_fc = await forecast_service.get_detailed_forecast(city=city, lat=req.latitude, lon=req.longitude, days=7)
        weather_res = await weather_service.get_forecast(city=city, lat=req.latitude, lon=req.longitude, days=5)
        curr = weather_res.current
        loc_name = weather_res.location.name

        # 4. Handle Dedicated Weekend Outlook
        if (entities.target_date == "weekend" or entities.intent == "weekend_forecast") and detailed_fc.weekend:
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
                    "target_date": "weekend",
                    "saturday": w_info.saturday.model_dump() if w_info.saturday else None,
                    "sunday": w_info.sunday.model_dump() if w_info.sunday else None,
                },
                source=detailed_fc.source,
                provider="Open-Meteo NWP Forecast Service",
                data_type="numerical_weather_prediction",
                is_official=False,
                is_llm_enhanced=entities.is_llm_enhanced,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        # 5. Extract Precise Forecast Time Slice (Never use current observations for future targets!)
        target_temp = curr.temperature
        target_feels = curr.feels_like
        target_humidity = curr.humidity
        target_wind = curr.wind_speed
        target_cond = curr.condition
        target_pop = 0.0
        data_source = curr.source if hasattr(curr, "source") else weather_res.source
        data_type = "observational_telemetry"

        if is_forecast_target and weather_res.forecast:
            data_type = "numerical_weather_prediction"
            target_time_hour = (
                8 if entities.target_time_slot == "morning"
                else (18 if entities.target_time_slot == "evening"
                      else (14 if entities.target_time_slot == "afternoon"
                            else (22 if entities.target_time_slot == "night" else 12)))
            )
            target_dt_str = self._calculate_target_date_string(entities.target_date)

            matching_items = [
                item for item in weather_res.forecast
                if target_dt_str in item.time
            ]

            if matching_items:
                # Find item closest to target hour
                best_item = min(
                    matching_items,
                    key=lambda x: abs(int(x.time.split(" ")[-1].split(":")[0] if " " in x.time else (x.time.split("T")[-1].split(":")[0] if "T" in x.time else 12)) - target_time_hour)
                )
                target_temp = best_item.temperature
                target_feels = best_item.feels_like or best_item.temperature
                target_humidity = best_item.humidity
                target_wind = best_item.wind_speed
                target_cond = best_item.condition
                target_pop = best_item.pop
            elif weather_res.forecast:
                # Fallback to earliest forecast item
                best_item = weather_res.forecast[0]
                target_temp = best_item.temperature
                target_feels = best_item.feels_like or best_item.temperature
                target_humidity = best_item.humidity
                target_wind = best_item.wind_speed
                target_cond = best_item.condition
                target_pop = best_item.pop

        # 6. Perform Weather Impact Intelligence Analysis
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

        risk_level = risk_analysis.risk_level
        risk_score = risk_analysis.score
        factors = risk_analysis.factors
        recommendation = risk_analysis.recommendation

        # 7. Synthesize Natural Language Answer with Explainability (WHY) & Actionable Advice
        answer = ""
        t_label = entities.target_date if entities.target_date != "today" else "today"

        # Outdoor Event Query
        if effective_activity == ActivityType.OUTDOOR_EVENT and ("suitable" in req.message.lower() or "event" in req.message.lower() or "function" in req.message.lower() or "nigarzhchi" in req.message.lower() or "karyakram" in req.message.lower()):
            suit_score, suit_label, suit_reason = forecast_service.calculate_event_suitability(
                temp_max=target_temp, max_pop=target_pop, max_wind=target_wind, condition=target_cond
            )
            if lang == "ta":
                answer = f"{loc_name} பகுதியில் {t_label} வெளிப்புற நிகழ்ச்சி ஏற்பாடு செய்ய வானிலை நிலை: {suit_label} (பொருத்தப்பாடு: {suit_score}%). {suit_reason} பரிந்துரை: {recommendation}"
            elif lang == "hi":
                answer = f"{loc_name} में {t_label} आउटडोर इवेंट के लिए मौसम की स्थिति: {suit_label} (उपयुक्तता स्कोर: {suit_score}%). {suit_reason} परामर्श: {recommendation}"
            else:
                answer = (
                    f"Outdoor Event Feasibility for {loc_name} ({t_label}): {suit_label} ({suit_score}% suitability). "
                    f"{suit_reason} Expected conditions: {target_temp}°C with {target_cond}, rain probability {int(target_pop * 100)}%, wind {target_wind} m/s. "
                    f"Actionable Advice: {recommendation}"
                )
        # Rain Inquiry / Umbrella Check
        elif entities.intent in ["rain_inquiry", "umbrella_check"]:
            has_rain = target_pop >= 0.35 or "rain" in target_cond.lower() or "drizzle" in target_cond.lower()
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
        # Activity Advisory (Running, Farming, Marine, Travel, Walking, etc.)
        elif entities.intent == "activity_advisory":
            if effective_activity == ActivityType.RUNNING:
                template_key = "running_advisory"
            elif effective_activity == ActivityType.FARMING:
                template_key = "farming_advisory"
            elif effective_activity == ActivityType.MARINE_ACTIVITY:
                template_key = "marine_advisory"
            elif effective_activity == ActivityType.TRAVELLING:
                template_key = "travel_advisory"
            else:
                template_key = "general_advisory"

            slot_str = f" {entities.target_time_slot}" if entities.target_time_slot != "now" else ""
            answer = multilingual_service.localize_response(
                lang=lang,
                template_key=template_key,
                replacements={
                    "location": loc_name,
                    "target": f"{t_label}{slot_str}",
                    "risk": risk_level.value,
                    "rec": recommendation,
                    "temp": target_temp,
                    "cond": target_cond,
                    "pop": int(target_pop * 100),
                    "humidity": target_humidity,
                    "wind": target_wind
                }
            )
        # Severe Warning Check
        elif entities.intent == "severe_warning_check":
            answer = f"No active official cyclone or extreme weather warnings are currently in effect for {loc_name}. (Source: Official IMD/NDMA warning bulletin)."
        # Forecast Inquiry
        elif entities.intent == "forecast":
            answer = (
                f"The forecast for {loc_name} for {entities.target_date} indicates a temperature around {target_temp}°C "
                f"with {target_cond}. Precipitation probability is {int(target_pop * 100)}% and wind is {target_wind} m/s."
            )
        # Temperature Inquiry
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
        # Default Current Weather
        else:
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
                "target_time_slot": entities.target_time_slot,
                "activity": entities.activity,
            },
            source=weather_res.source,
            provider="OpenWeather / Open-Meteo Hybrid",
            data_type=data_type,
            is_official=False,
            is_llm_enhanced=entities.is_llm_enhanced,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


ai_service = AIService()
