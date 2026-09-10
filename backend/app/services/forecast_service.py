from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.services.weather_service import weather_service
from app.schemas.weather import (
    NormalizedWeatherResponse,
    DetailedForecastResponse,
    DailyForecastSummary,
    DayPartForecast,
    WeekendForecastSummary,
    ForecastItem,
)
import logging

logger = logging.getLogger(__name__)


class ForecastService:
    """
    Dedicated Meteorological Forecast Service.
    Produces high-resolution daily aggregations, time-of-day interval breakdowns,
    outdoor event suitability metrics, and weekend outlooks.
    """

    def calculate_event_suitability(
        self, temp_max: float, max_pop: float, max_wind: float, condition: str
    ) -> tuple[int, str, str]:
        """
        Calculates 0-100 outdoor event suitability score, categorical label, and reason.
        Strictly rule-based decision support metric based on meteorological thresholds.
        """
        score = 100
        reasons = []

        # Precipitation Impact
        if max_pop >= 0.70:
            score -= 50
            reasons.append(f"High rain probability ({int(max_pop * 100)}%)")
        elif max_pop >= 0.40:
            score -= 25
            reasons.append(f"Moderate chance of rain ({int(max_pop * 100)}%)")
        elif max_pop >= 0.20:
            score -= 10
            reasons.append(f"Slight possibility of showers ({int(max_pop * 100)}%)")

        # Temperature / Thermal Stress Impact
        if temp_max >= 40.0:
            score -= 40
            reasons.append(f"Dangerous extreme heat ({round(temp_max)}°C)")
        elif temp_max >= 35.0:
            score -= 20
            reasons.append(f"Elevated daytime temperatures ({round(temp_max)}°C)")
        elif temp_max < 12.0:
            score -= 20
            reasons.append(f"Chilly temperatures ({round(temp_max)}°C)")

        # Wind Gust Impact
        if max_wind >= 12.0:
            score -= 30
            reasons.append(f"Strong wind gusts (~{round(max_wind * 3.6)} km/h)")
        elif max_wind >= 8.0:
            score -= 10
            reasons.append(f"Breezy conditions (~{round(max_wind * 3.6)} km/h)")

        # Thunderstorm condition
        if "thunder" in condition.lower() or "storm" in condition.lower():
            score = min(score, 20)
            reasons.append("Thunderstorm risk detected")

        final_score = max(5, min(100, score))

        if final_score >= 80:
            label = "Optimal"
            explanation = "Excellent weather conditions for outdoor events with low precipitation risk."
        elif final_score >= 60:
            label = "Favorable"
            explanation = f"Generally favorable for outdoor gatherings. Note: {', '.join(reasons)}."
        elif final_score >= 40:
            label = "Moderate Caution"
            explanation = f"Conditions require secondary planning: {', '.join(reasons)}."
        else:
            label = "Unfavorable / High Risk"
            explanation = f"High disruption potential for outdoor events due to {', '.join(reasons)}. Covered backup recommended."

        return final_score, label, explanation

    def _extract_day_parts(self, items: List[ForecastItem]) -> List[DayPartForecast]:
        """Divides items into Morning (06:00-11:59), Afternoon (12:00-16:59), Evening (17:00-21:59), Night (22:00-05:59)."""
        slots: Dict[str, Dict[str, Any]] = {
            "morning": {"label": "Morning (06:00 - 12:00)", "items": []},
            "afternoon": {"label": "Afternoon (12:00 - 17:00)", "items": []},
            "evening": {"label": "Evening (17:00 - 22:00)", "items": []},
            "night": {"label": "Night (22:00 - 06:00)", "items": []},
        }

        for item in items:
            # Parse hour
            time_part = item.time.split(" ")[-1] if " " in item.time else item.time.split("T")[-1]
            try:
                hour = int(time_part.split(":")[0])
            except Exception:
                hour = 12

            if 6 <= hour < 12:
                slots["morning"]["items"].append(item)
            elif 12 <= hour < 17:
                slots["afternoon"]["items"].append(item)
            elif 17 <= hour < 22:
                slots["evening"]["items"].append(item)
            else:
                slots["night"]["items"].append(item)

        result_parts: List[DayPartForecast] = []
        for part_key, part_info in slots.items():
            p_items: List[ForecastItem] = part_info["items"]
            if not p_items:
                # If no interval fell in slot, take nearest
                sample = items[0] if items else None
                if sample:
                    result_parts.append(
                        DayPartForecast(
                            part=part_key,
                            label=part_info["label"],
                            temperature=sample.temperature,
                            feels_like=sample.feels_like or sample.temperature,
                            condition=sample.condition,
                            humidity=sample.humidity,
                            wind_speed=sample.wind_speed,
                            pop=sample.pop,
                            rain_mm=sample.rain_mm or 0.0,
                        )
                    )
            else:
                mid = p_items[len(p_items) // 2]
                avg_t = sum(i.temperature for i in p_items) / len(p_items)
                max_pop = max(i.pop for i in p_items)
                tot_rain = sum(i.rain_mm or 0.0 for i in p_items)
                avg_h = int(sum(i.humidity for i in p_items) / len(p_items))
                avg_w = round(sum(i.wind_speed for i in p_items) / len(p_items), 1)

                result_parts.append(
                    DayPartForecast(
                        part=part_key,
                        label=part_info["label"],
                        temperature=round(avg_t, 1),
                        feels_like=round(mid.feels_like or avg_t, 1),
                        condition=mid.condition,
                        humidity=avg_h,
                        wind_speed=avg_w,
                        pop=round(max_pop, 2),
                        rain_mm=round(tot_rain, 1),
                    )
                )

        return result_parts

    async def get_detailed_forecast(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 7,
    ) -> DetailedForecastResponse:
        """Constructs rich daily aggregations, day-part breakdown, and weekend forecast."""
        normalized: NormalizedWeatherResponse = await weather_service.get_forecast(
            city=city, lat=lat, lon=lon, days=days
        )

        # Group by date
        grouped: Dict[str, List[ForecastItem]] = {}
        for item in normalized.forecast:
            d_str = item.time.split(" ")[0] if " " in item.time else item.time.split("T")[0]
            if d_str not in grouped:
                grouped[d_str] = []
            grouped[d_str].append(item)

        daily_summaries: List[DailyForecastSummary] = []
        sat_summary: Optional[DailyForecastSummary] = None
        sun_summary: Optional[DailyForecastSummary] = None

        for d_str, items in grouped.items():
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            day_name = dt.strftime("%A")

            temps = [i.temperature for i in items]
            min_t = min(temps)
            max_t = max(temps)
            avg_t = round(sum(temps) / len(temps), 1)
            avg_h = int(sum(i.humidity for i in items) / len(items))
            max_w = max(i.wind_speed for i in items)
            max_p = max(i.pop for i in items)
            tot_r = round(sum(i.rain_mm or 0.0 for i in items), 1)

            # Dominant condition (midday or most severe)
            dom_item = items[len(items) // 2]
            cond = dom_item.condition

            suit_score, suit_label, suit_reason = self.calculate_event_suitability(
                temp_max=max_t, max_pop=max_p, max_wind=max_w, condition=cond
            )

            parts = self._extract_day_parts(items)

            summary = DailyForecastSummary(
                date=d_str,
                day_name=day_name,
                temp_min=round(min_t, 1),
                temp_max=round(max_t, 1),
                avg_temp=avg_t,
                avg_humidity=avg_h,
                max_wind=round(max_w, 1),
                max_pop=round(max_p, 2),
                total_rain_mm=tot_r,
                overall_condition=cond,
                event_suitability_score=suit_score,
                event_suitability_label=suit_label,
                event_suitability_reason=suit_reason,
                parts=parts,
            )

            daily_summaries.append(summary)

            if day_name == "Saturday" and not sat_summary:
                sat_summary = summary
            elif day_name == "Sunday" and not sun_summary:
                sun_summary = summary

        # Build Weekend Outlook
        weekend_obj = None
        if sat_summary or sun_summary:
            sat_desc = (
                f"Saturday: {round(sat_summary.temp_max)}°C with {sat_summary.overall_condition}, {int(sat_summary.max_pop * 100)}% rain chance."
                if sat_summary else "Saturday forecast pending."
            )
            sun_desc = (
                f"Sunday: {round(sun_summary.temp_max)}°C with {sun_summary.overall_condition}, {int(sun_summary.max_pop * 100)}% rain chance."
                if sun_summary else "Sunday forecast pending."
            )
            verdict = f"{sat_desc} {sun_desc}"

            # Recommendation
            highest_rain = max(sat_summary.max_pop if sat_summary else 0, sun_summary.max_pop if sun_summary else 0)
            if highest_rain >= 0.5:
                rec = "Weekend outdoor plans should include rain backup options or rain gear."
            else:
                rec = "Weather across the weekend looks favorable for travel, sports, and outdoor gatherings."

            weekend_obj = WeekendForecastSummary(
                available=True,
                saturday=sat_summary,
                sunday=sun_summary,
                weekend_verdict=verdict,
                outdoor_recommendation=rec,
            )

        return DetailedForecastResponse(
            location=normalized.location,
            days=daily_summaries,
            weekend=weekend_obj,
            source=normalized.source,
            attribution_notes=normalized.attribution_notes,
        )


forecast_service = ForecastService()
