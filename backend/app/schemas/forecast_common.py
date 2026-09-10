from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CommonForecastItem(BaseModel):
    """
    Common normalized forecast representation across all NWP and observational models.
    Strictly preserves nulls where variables are not provided by a specific model.
    """
    provider: str = Field(..., description="Provider identifier, e.g., 'open_meteo', 'gfs', 'wrf', 'openweather'")
    model: str = Field(..., description="Specific model name, e.g., 'GFS 0.25°', 'WRF-ARW 3km', 'ECMWF/Open-Meteo'")
    source: str = Field(..., description="Meteorological authority or agency source")
    run_time: Optional[str] = Field(None, description="Model run/cycle identifier, e.g. '00Z', '12Z'")
    forecast_time: str = Field(..., description="Target forecast timestamp in ISO format")
    latitude: float = Field(..., description="Grid cell latitude")
    longitude: float = Field(..., description="Grid cell longitude")
    
    temperature: Optional[float] = Field(None, description="2m temperature in Celsius")
    feels_like: Optional[float] = Field(None, description="Apparent temperature in Celsius")
    humidity: Optional[int] = Field(None, description="Relative humidity percentage (0-100)")
    precipitation: Optional[float] = Field(None, description="Precipitation rate/depth in mm")
    precipitation_probability: Optional[float] = Field(None, description="Precipitation probability (0.0 to 1.0)")
    wind_speed: Optional[float] = Field(None, description="Wind speed in m/s")
    wind_direction: Optional[float] = Field(None, description="Wind direction in degrees (0-360)")
    pressure: Optional[float] = Field(None, description="Surface atmospheric pressure in hPa")
    visibility: Optional[float] = Field(None, description="Horizontal visibility in meters")
    condition: Optional[str] = Field(None, description="Descriptive meteorological condition")
    cape: Optional[float] = Field(None, description="Convective Available Potential Energy in J/kg")
    
    available_variables: List[str] = Field(default_factory=list, description="List of valid variables provided by this model")


class CommonModelForecastResponse(BaseModel):
    """
    Standard response format for individual NWP/weather model forecasts.
    Returns structured unavailable states without fabricated values when data is absent.
    """
    provider: str
    model: str
    source: str
    available: bool = False
    configured: bool = False
    status: str = "Active"
    resolution: Optional[str] = None
    run_time: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    forecast_items: List[CommonForecastItem] = []
    attribution_notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelComparisonInterval(BaseModel):
    """Interval comparison across models for a specific timestamp."""
    time: str
    consensus_temp: Optional[float] = None
    consensus_precipitation: Optional[float] = None
    consensus_wind_speed: Optional[float] = None
    model_values: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    temp_spread: Optional[float] = None
    disagreement: Optional[str] = None


class ModelComparisonResponse(BaseModel):
    """
    Multi-model consensus and agreement comparison output.
    Provides explainable, deterministic confidence metrics without synthetic confidence.
    """
    location: Dict[str, Any]
    models_total: int
    models_available_count: int
    models_available: List[str]
    models_unavailable: List[Dict[str, Any]] = Field(default_factory=list)
    consensus_status: str
    agreement_score: Optional[float] = Field(None, description="Deterministic agreement score (0.0-1.0), None for single provider")
    confidence: str = Field(..., description="High, Moderate, Low, or Unavailable (single provider)")
    disagreements: List[str] = Field(default_factory=list)
    summary: str
    intervals: List[ModelComparisonInterval] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
