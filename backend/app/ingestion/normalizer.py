from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.forecast_common import CommonForecastItem


class DataNormalizer:
    """Normalizes raw heterogeneous meteorological feeds into standardized WeatherGPT schemas."""

    @staticmethod
    def kelvin_to_celsius(temp_k: Optional[float]) -> Optional[float]:
        if temp_k is None:
            return None
        return round(temp_k - 273.15, 1)

    @staticmethod
    def kmh_to_ms(speed_kmh: Optional[float]) -> Optional[float]:
        if speed_kmh is None:
            return None
        return round(speed_kmh / 3.6, 1)

    @staticmethod
    def pa_to_hpa(pressure_pa: Optional[float]) -> Optional[float]:
        if pressure_pa is None:
            return None
        return round(pressure_pa / 100.0, 1)

    @classmethod
    def to_common_item(
        cls,
        provider: str,
        model: str,
        source: str,
        forecast_time: str,
        latitude: float,
        longitude: float,
        temperature: Optional[float] = None,
        feels_like: Optional[float] = None,
        humidity: Optional[int] = None,
        precipitation: Optional[float] = None,
        wind_speed: Optional[float] = None,
        wind_direction: Optional[float] = None,
        pressure: Optional[float] = None,
        condition: Optional[str] = None,
        cape: Optional[float] = None,
        run_time: Optional[str] = None,
    ) -> CommonForecastItem:
        """Constructs a validated CommonForecastItem tracking available non-null variables."""
        avail = []
        if temperature is not None:
            avail.append("temperature")
        if feels_like is not None:
            avail.append("feels_like")
        if humidity is not None:
            avail.append("humidity")
        if precipitation is not None:
            avail.append("precipitation")
        if wind_speed is not None:
            avail.append("wind_speed")
        if wind_direction is not None:
            avail.append("wind_direction")
        if pressure is not None:
            avail.append("pressure")
        if condition is not None:
            avail.append("condition")
        if cape is not None:
            avail.append("cape")

        return CommonForecastItem(
            provider=provider,
            model=model,
            source=source,
            run_time=run_time,
            forecast_time=forecast_time,
            latitude=latitude,
            longitude=longitude,
            temperature=temperature,
            feels_like=feels_like,
            humidity=humidity,
            precipitation=precipitation,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            pressure=pressure,
            condition=condition,
            cape=cape,
            available_variables=avail,
        )
