from typing import List, Optional
from pydantic import BaseModel, Field


class ClimateDataPoint(BaseModel):
    year: int
    month: Optional[int] = None
    label: str
    avg_temp: float = Field(..., description="Mean temperature in Celsius")
    max_temp: Optional[float] = None
    min_temp: Optional[float] = None
    total_rainfall_mm: Optional[float] = None
    anomaly: Optional[float] = Field(None, description="Temperature anomaly compared to long-term baseline")


class ClimateTrendResponse(BaseModel):
    available: bool = True
    message: Optional[str] = None
    location: str
    latitude: float
    longitude: float
    period: Optional[str] = None  # e.g., "1994 - 2024 (30-year trend)"
    baseline_avg_temp: Optional[float] = None
    recent_avg_temp: Optional[float] = None
    temp_change_rate: Optional[float] = Field(None, description="Degrees Celsius increase/decade")
    trend_summary: Optional[str] = None
    data_points: List[ClimateDataPoint] = []
    source: str = "Open-Meteo Historical Climate Reanalysis (ERA5) / Meteorological Archive"
    provider: str = "Open-Meteo Historical Climate Service"
    data_type: str = "historical_reanalysis"
    is_official: bool = False
    citation: str = "Historical observational climate reanalysis data. Not a predictive forecast."
    timestamp: Optional[str] = None
