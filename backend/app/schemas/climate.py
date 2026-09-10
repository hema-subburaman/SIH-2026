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
    location: str
    latitude: float
    longitude: float
    period: str  # e.g., "1994 - 2024 (30-year trend)"
    baseline_avg_temp: float
    recent_avg_temp: float
    temp_change_rate: float = Field(..., description="Degrees Celsius increase/decade")
    trend_summary: str
    data_points: List[ClimateDataPoint] = []
    source: str = "Open-Meteo Historical Climate Reanalysis (ERA5) / Meteorological Archive"
    citation: str = "Historical observational climate reanalysis data. Not a predictive forecast."
