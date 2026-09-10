from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AlertCategory(str, Enum):
    HEAVY_RAINFALL = "Heavy Rainfall"
    THUNDERSTORM = "Thunderstorm / Lightning"
    CYCLONE = "Cyclone Warning"
    STRONG_WINDS = "Strong / Gale Winds"
    EXTREME_HEAT = "Extreme Heat / Heatwave"
    FLOOD = "Flood Warning"
    DENSE_FOG = "Dense Fog / Low Visibility"
    SYSTEM_RISK = "System Weather Risk"


class AlertSeverity(str, Enum):
    WARNING = "Warning"        # Red / Severe
    WATCH = "Watch"            # Orange / Moderate
    ADVISORY = "Advisory"      # Yellow / Minor
    STATEMENT = "Statement"    # Informational


class AlertItem(BaseModel):
    id: str
    event: str = Field(..., description="e.g. Cyclone Warning, Heatwave Alert")
    category: AlertCategory
    severity: AlertSeverity
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    headline: Optional[str] = None
    description: str
    recommendation: str
    is_official: bool = Field(..., description="True if from official meteorological agency (IMD/Govt)")
    source: str = Field(..., description="Issuing authority name and source URL/reference")


class AlertsResponse(BaseModel):
    location: str
    total_active: int
    official_alerts: List[AlertItem] = []
    system_risks: List[AlertItem] = []
    source: str
    note: str = (
        "Official warnings are sourced from authorized meteorological bodies (such as IMD). "
        "System weather risks are algorithmically derived from live threshold exceedances."
    )
