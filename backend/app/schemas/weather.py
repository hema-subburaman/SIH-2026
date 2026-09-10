from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class LocationInfo(BaseModel):
    name: str
    state: Optional[str] = None
    country: Optional[str] = "IN"
    latitude: float
    longitude: float


class CurrentWeather(BaseModel):
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels-like temperature in Celsius")
    humidity: int = Field(..., description="Relative humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_deg: Optional[float] = Field(None, description="Wind direction in degrees")
    visibility: Optional[float] = Field(None, description="Visibility in meters")
    condition: str = Field(..., description="Weather condition description")
    condition_code: Optional[str] = Field(None, description="Standard weather code / icon key")
    pressure: Optional[float] = Field(None, description="Atmospheric pressure in hPa")
    uv_index: Optional[float] = Field(None, description="UV Index (0-12)")
    precipitation_mm: Optional[float] = Field(0.0, description="Precipitation in last hour (mm)")
    sunrise: Optional[str] = Field(None, description="Local sunrise time ISO/HH:MM")
    sunset: Optional[str] = Field(None, description="Local sunset time ISO/HH:MM")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ForecastItem(BaseModel):
    time: str = Field(..., description="Forecast timestamp in ISO format")
    temperature: float = Field(..., description="Forecast temperature in Celsius")
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: int
    wind_speed: float
    wind_deg: Optional[float] = None
    condition: str
    condition_code: Optional[str] = None
    pop: float = Field(default=0.0, description="Probability of precipitation (0.0 to 1.0)")
    rain_mm: Optional[float] = Field(default=0.0, description="Predicted rainfall in mm")


class NormalizedWeatherResponse(BaseModel):
    location: LocationInfo
    current: CurrentWeather
    forecast: List[ForecastItem] = []
    alerts: List[dict] = []
    source: str = Field(..., description="Meteorological data source citation")
    attribution_notes: Optional[str] = None
    cached: bool = False


class DayPartForecast(BaseModel):
    part: str = Field(..., description="morning, afternoon, evening, night")
    label: str
    temperature: float
    feels_like: float
    condition: str
    humidity: int
    wind_speed: float
    pop: float = Field(default=0.0, description="Precipitation probability (0.0 to 1.0)")
    rain_mm: float = 0.0


class DailyForecastSummary(BaseModel):
    date: str
    day_name: str
    temp_min: float
    temp_max: float
    avg_temp: float
    avg_humidity: int
    max_wind: float
    max_pop: float
    total_rain_mm: float
    overall_condition: str
    event_suitability_score: int = Field(..., description="0 to 100 outdoor event suitability")
    event_suitability_label: str
    event_suitability_reason: str
    parts: List[DayPartForecast] = []


class WeekendForecastSummary(BaseModel):
    available: bool = True
    saturday: Optional[DailyForecastSummary] = None
    sunday: Optional[DailyForecastSummary] = None
    weekend_verdict: str
    outdoor_recommendation: str


class DetailedForecastResponse(BaseModel):
    location: LocationInfo
    days: List[DailyForecastSummary] = []
    weekend: Optional[WeekendForecastSummary] = None
    source: str
    attribution_notes: Optional[str] = None

