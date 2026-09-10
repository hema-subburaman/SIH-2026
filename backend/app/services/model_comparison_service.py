from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from app.providers.open_meteo import OpenMeteoProvider
from app.providers.openweather import OpenWeatherProvider
from app.providers.gfs_provider import GFSProvider
from app.providers.wrf_provider import WRFProvider
from app.schemas.forecast_common import (
    CommonModelForecastResponse,
    CommonForecastItem,
    ModelComparisonResponse,
    ModelComparisonInterval,
)

logger = logging.getLogger(__name__)


class ModelComparisonService:
    """
    Multi-Model Meteorological Comparison & Deterministic Consensus Service.
    Compares real numerical weather predictions across Open-Meteo, NOAA GFS, WRF-ARW, and OpenWeather.
    
    CRITICAL: Strict zero-fabrication policy.
    - If only 1 model is available: explicitly states consensus is unavailable.
    - If models disagree: flags the specific variable-level divergences.
    - Confidence is strictly deterministic, explainable, and derived solely from real model outputs.
    """

    def __init__(self):
        self.open_meteo = OpenMeteoProvider()
        self.openweather = OpenWeatherProvider()
        self.gfs = GFSProvider()
        self.wrf = WRFProvider()

    async def compare_forecasts(
        self,
        lat: float,
        lon: float,
        location_name: str = "Location",
        days: int = 5,
    ) -> ModelComparisonResponse:
        """
        Retrieves forecasts from all active/configured models, normalizes them into the
        Common Forecast Schema, and executes deterministic agreement and consensus analysis.
        """
        # Step 1: Query all providers concurrently or safely
        model_results: Dict[str, CommonModelForecastResponse] = {}

        # 1. Open-Meteo
        try:
            model_results["Open-Meteo"] = await self.open_meteo.get_common_forecast(lat=lat, lon=lon, days=days)
        except Exception as ex:
            logger.warning(f"Open-Meteo query failed: {ex}")
            model_results["Open-Meteo"] = CommonModelForecastResponse(
                provider="open_meteo",
                model="Open-Meteo Multi-Model",
                source="Open-Meteo",
                available=False,
                status=str(ex),
                forecast_items=[],
            )

        # 2. NOAA GFS
        try:
            model_results["GFS"] = await self.gfs.get_common_forecast(lat=lat, lon=lon, days=days)
        except Exception as ex:
            logger.warning(f"GFS query failed: {ex}")
            model_results["GFS"] = CommonModelForecastResponse(
                provider="gfs",
                model="NOAA GFS 0.25°",
                source="NOAA GFS",
                available=False,
                status=str(ex),
                forecast_items=[],
            )

        # 3. WRF Meso-Scale
        try:
            model_results["WRF"] = await self.wrf.get_common_forecast(lat=lat, lon=lon, days=days)
        except Exception as ex:
            logger.warning(f"WRF query failed: {ex}")
            model_results["WRF"] = CommonModelForecastResponse(
                provider="wrf",
                model="WRF-ARW 3km",
                source="WRF Meso-scale",
                available=False,
                status=str(ex),
                forecast_items=[],
            )

        # 4. OpenWeather
        try:
            model_results["OpenWeather"] = await self.openweather.get_common_forecast(lat=lat, lon=lon, days=days)
        except Exception as ex:
            logger.warning(f"OpenWeather query failed: {ex}")
            model_results["OpenWeather"] = CommonModelForecastResponse(
                provider="openweather",
                model="OpenWeather",
                source="OpenWeather API",
                available=False,
                status=str(ex),
                forecast_items=[],
            )

        # Step 2: Categorize available vs unavailable models
        available_models = [name for name, resp in model_results.items() if resp.available and len(resp.forecast_items) > 0]
        unavailable_models = [
            {"model": name, "source": resp.source, "status": resp.status, "configured": resp.configured}
            for name, resp in model_results.items()
            if not resp.available or len(resp.forecast_items) == 0
        ]

        total_models = len(model_results)
        available_count = len(available_models)

        loc_meta = {
            "name": location_name,
            "latitude": lat,
            "longitude": lon,
        }

        # Case 1: Zero models available
        if available_count == 0:
            return ModelComparisonResponse(
                location=loc_meta,
                models_total=total_models,
                models_available_count=0,
                models_available=[],
                models_unavailable=unavailable_models,
                consensus_status="NO_DATA",
                agreement_score=None,
                confidence="Unavailable",
                disagreements=["No numerical weather prediction models currently reachable."],
                summary="All forecast models are currently unreachable or unconfigured. Real-time consensus cannot be computed.",
                intervals=[],
            )

        # Case 2: Exactly 1 model available -> NO FABRICATED CONSENSUS CONFIDENCE
        if available_count == 1:
            single_name = available_models[0]
            single_resp = model_results[single_name]
            intervals = [
                ModelComparisonInterval(
                    time=item.forecast_time,
                    consensus_temp=item.temperature,
                    consensus_precipitation=item.precipitation,
                    consensus_wind_speed=item.wind_speed,
                    model_values={single_name: {"temp": item.temperature, "precip": item.precipitation, "wind": item.wind_speed}},
                    temp_spread=0.0,
                    disagreement=None,
                )
                for item in single_resp.forecast_items[:8]
            ]

            return ModelComparisonResponse(
                location=loc_meta,
                models_total=total_models,
                models_available_count=1,
                models_available=available_models,
                models_unavailable=unavailable_models,
                consensus_status="SINGLE_PROVIDER",
                agreement_score=None,
                confidence="Single-provider forecast. Model consensus confidence is unavailable.",
                disagreements=[],
                summary=f"Forecast provided solely by {single_name}. Multi-model consensus comparison is unavailable because only one provider is active.",
                intervals=intervals,
            )

        # Case 3: >= 2 models available -> Execute deterministic comparison
        # Group forecast items by approximate time key (YYYY-MM-DDTHH)
        time_buckets: Dict[str, Dict[str, CommonForecastItem]] = {}
        for m_name in available_models:
            for item in model_results[m_name].forecast_items:
                # Normalize time bucket to first 13 chars: YYYY-MM-DDTHH
                t_clean = item.forecast_time.replace(" ", "T")
                bucket_key = t_clean[:13] if len(t_clean) >= 13 else t_clean
                if bucket_key not in time_buckets:
                    time_buckets[bucket_key] = {}
                time_buckets[bucket_key][m_name] = item

        intervals: List[ModelComparisonInterval] = []
        temp_agreements: List[float] = []
        precip_agreements: List[float] = []
        wind_agreements: List[float] = []
        disagreements_found: List[str] = []

        # Sort time buckets
        sorted_keys = sorted(time_buckets.keys())[:16]  # Compare next 48-72 hours

        for key in sorted_keys:
            items_in_bucket = time_buckets[key]
            # Only compare if at least 2 models reported for this interval
            if len(items_in_bucket) < 2:
                continue

            temps = [it.temperature for it in items_in_bucket.values() if it.temperature is not None]
            precips = [it.precipitation for it in items_in_bucket.values() if it.precipitation is not None]
            winds = [it.wind_speed for it in items_in_bucket.values() if it.wind_speed is not None]

            # Temperature comparison
            t_spread = None
            avg_temp = None
            if temps:
                avg_temp = round(sum(temps) / len(temps), 1)
                t_spread = round(max(temps) - min(temps), 1)
                # Spread <= 2°C is high agreement (1.0), 2-4°C is moderate (0.7), >4°C is divergent (0.3)
                if t_spread <= 2.0:
                    temp_agreements.append(1.0)
                elif t_spread <= 4.0:
                    temp_agreements.append(0.7)
                else:
                    temp_agreements.append(0.3)
                    t_dis = f"Temperature divergence of {t_spread}°C around {key}:00 (Models: {', '.join([f'{m}: {it.temperature}°C' for m, it in items_in_bucket.items() if it.temperature is not None])})"
                    if t_dis not in disagreements_found:
                        disagreements_found.append(t_dis)

            # Precipitation comparison (rain vs dry threshold >= 0.5mm)
            avg_precip = None
            interval_disagreement = None
            if precips:
                avg_precip = round(sum(precips) / len(precips), 1)
                rain_states = [p >= 0.5 for p in precips]
                all_rain = all(rain_states)
                all_dry = not any(rain_states)
                if all_rain or all_dry:
                    precip_agreements.append(1.0)
                else:
                    # Model split on rain
                    precip_agreements.append(0.2)
                    p_models = [f"{m}: {it.precipitation}mm" for m, it in items_in_bucket.items() if it.precipitation is not None]
                    interval_disagreement = f"Precipitation split: {', '.join(p_models)}"
                    p_dis = f"Disagreement on precipitation around {key}:00 ({', '.join(p_models)})"
                    if p_dis not in disagreements_found:
                        disagreements_found.append(p_dis)

            # Wind comparison
            avg_wind = None
            if winds:
                avg_wind = round(sum(winds) / len(winds), 1)
                w_spread = max(winds) - min(winds)
                if w_spread <= 3.0:
                    wind_agreements.append(1.0)
                else:
                    wind_agreements.append(max(0.2, 1.0 - (w_spread / 10.0)))

            # Per-interval entry
            m_values = {
                m: {"temp": it.temperature, "precip": it.precipitation, "wind": it.wind_speed}
                for m, it in items_in_bucket.items()
            }

            intervals.append(
                ModelComparisonInterval(
                    time=f"{key}:00",
                    consensus_temp=avg_temp,
                    consensus_precipitation=avg_precip,
                    consensus_wind_speed=avg_wind,
                    model_values=m_values,
                    temp_spread=t_spread,
                    disagreement=interval_disagreement,
                )
            )

        # Compute deterministic overall agreement score
        avg_t_score = sum(temp_agreements) / max(1, len(temp_agreements)) if temp_agreements else 1.0
        avg_p_score = sum(precip_agreements) / max(1, len(precip_agreements)) if precip_agreements else 1.0
        avg_w_score = sum(wind_agreements) / max(1, len(wind_agreements)) if wind_agreements else 1.0

        # Weighted agreement: Temperature 40%, Precipitation 45%, Wind 15%
        overall_agreement = round(0.40 * avg_t_score + 0.45 * avg_p_score + 0.15 * avg_w_score, 2)

        # Explainable confidence categorization
        if overall_agreement >= 0.85:
            confidence = "High"
            summary_desc = f"Strong consensus across {available_count} models ({', '.join(available_models)}). Models exhibit high agreement on thermal and precipitation patterns."
        elif overall_agreement >= 0.60:
            confidence = "Moderate"
            summary_desc = f"Moderate consensus across {available_count} models ({', '.join(available_models)}). Minor divergence detected in precipitation intensity or temperature timing."
        else:
            confidence = "Low"
            summary_desc = f"Low consensus across {available_count} models ({', '.join(available_models)}). Notable disagreements detected between model simulations."

        if disagreements_found:
            summary_desc += f" Key observations: {disagreements_found[0]}."

        return ModelComparisonResponse(
            location=loc_meta,
            models_total=total_models,
            models_available_count=available_count,
            models_available=available_models,
            models_unavailable=unavailable_models,
            consensus_status="CONSENSUS_AVAILABLE",
            agreement_score=overall_agreement,
            confidence=confidence,
            disagreements=disagreements_found[:5],  # top 5 key disagreements
            summary=summary_desc,
            intervals=intervals,
        )


model_comparison_service = ModelComparisonService()
