from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MeteorologicalValidator:
    """
    Validates meteorological observations and numerical forecasts against physical bounds.
    Rejects corrupted data points, impossible values, and duplicate timestamps.
    """

    # Atmospheric bounds for Earth troposphere / surface observations
    TEMP_MIN_C = -90.0
    TEMP_MAX_C = 65.0
    HUMIDITY_MIN = 0
    HUMIDITY_MAX = 100
    WIND_SPEED_MAX_MS = 120.0  # ~432 km/h (Cat 5 Hurricane / Tornado)
    PRESSURE_MIN_HPA = 800.0   # Extremely deep cyclone
    PRESSURE_MAX_HPA = 1090.0  # Siberian High extreme
    PRECIPITATION_MAX_MM = 500.0  # Extreme hourly cloudburst ceiling

    @classmethod
    def validate_observation(cls, obs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates a single observation or forecast item. Returns (is_valid, error_list)."""
        errors: List[str] = []

        temp = obs.get("temperature")
        if temp is not None:
            if not isinstance(temp, (int, float)) or temp < cls.TEMP_MIN_C or temp > cls.TEMP_MAX_C:
                errors.append(f"Temperature out of physical bounds: {temp}°C (Allowed: {cls.TEMP_MIN_C} to {cls.TEMP_MAX_C})")

        humidity = obs.get("humidity")
        if humidity is not None:
            if not isinstance(humidity, (int, float)) or humidity < cls.HUMIDITY_MIN or humidity > cls.HUMIDITY_MAX:
                errors.append(f"Humidity out of bounds: {humidity}% (Allowed: 0 to 100)")

        wind = obs.get("wind_speed")
        if wind is not None:
            if not isinstance(wind, (int, float)) or wind < 0.0 or wind > cls.WIND_SPEED_MAX_MS:
                errors.append(f"Wind speed out of bounds: {wind} m/s (Allowed: 0 to {cls.WIND_SPEED_MAX_MS})")

        pressure = obs.get("pressure")
        if pressure is not None:
            if not isinstance(pressure, (int, float)) or pressure < cls.PRESSURE_MIN_HPA or pressure > cls.PRESSURE_MAX_HPA:
                errors.append(f"Pressure out of physical bounds: {pressure} hPa")

        precip = obs.get("precipitation")
        if precip is not None:
            if not isinstance(precip, (int, float)) or precip < 0.0 or precip > cls.PRECIPITATION_MAX_MM:
                errors.append(f"Precipitation out of bounds: {precip} mm")

        return (len(errors) == 0, errors)

    @classmethod
    def deduplicate_records(
        cls, records: List[Dict[str, Any]], key_field: str = "time"
    ) -> List[Dict[str, Any]]:
        """Filters out duplicate timestamped records, keeping the most recently ingested record."""
        seen = set()
        deduped = []
        for r in records:
            k = r.get(key_field)
            if k and k in seen:
                continue
            if k:
                seen.add(k)
            deduped.append(r)
        return deduped
