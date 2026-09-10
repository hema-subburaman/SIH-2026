from typing import List, Optional, Dict, Any, Set
from fastapi import WebSocket
from datetime import datetime
from app.providers.imd_warning_provider import OfficialMeteorologicalWarningProvider
from app.services.weather_service import weather_service
from app.schemas.alert import AlertItem, AlertCategory, AlertSeverity, AlertsResponse
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self):
        self.official_provider = OfficialMeteorologicalWarningProvider()
        # Active websocket connections for live alert dissemination
        self.active_connections: Set[WebSocket] = set()

    async def connect_ws(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect_ws(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_alert(self, alert_payload: Dict[str, Any]):
        message = json.dumps(alert_payload)
        for conn in list(self.active_connections):
            try:
                await conn.send_text(message)
            except Exception:
                self.disconnect_ws(conn)

    async def get_alerts_for_location(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> AlertsResponse:
        # 1. Fetch Official Warnings from IMD / Warning Feed
        official_alerts: List[AlertItem] = await self.official_provider.get_alerts(city=city, lat=lat, lon=lon)

        # 2. Derive System Weather Risks from live threshold conditions
        # (Explicitly tagged as system algorithmic risks, NOT government orders)
        system_risks: List[AlertItem] = []
        try:
            curr_data = await weather_service.get_current_weather(city=city, lat=lat, lon=lon)
            curr = curr_data.current
            loc = curr_data.location

            # Evaluate extreme heat
            if curr.temperature >= settings.HEAT_DANGER_TEMP or curr.feels_like >= 42.0:
                system_risks.append(
                    AlertItem(
                        id=f"sys-heat-{int(datetime.utcnow().timestamp())}",
                        event="Extreme Thermal Exceedance Risk",
                        category=AlertCategory.EXTREME_HEAT,
                        severity=AlertSeverity.WARNING if curr.temperature >= 42 else AlertSeverity.WATCH,
                        location=loc.name,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        headline=f"Elevated Heat Index ({curr.feels_like}°C) Detected",
                        description=(
                            f"Current ambient temperature is {curr.temperature}°C with relative humidity at {curr.humidity}%. "
                            "Algorithmic heat stress index exceeds critical safe baseline."
                        ),
                        recommendation="Avoid strenuous outdoor activities during peak hours (11:00 AM - 3:30 PM). Stay hydrated.",
                        is_official=False,
                        source="WeatherGPT Algorithmic Impact Engine (Rule-based Threshold)",
                    )
                )

            # Evaluate gale wind
            if curr.wind_speed >= settings.WIND_GALE_MIN:
                system_risks.append(
                    AlertItem(
                        id=f"sys-wind-{int(datetime.utcnow().timestamp())}",
                        event="High Wind Gust Hazard",
                        category=AlertCategory.STRONG_WINDS,
                        severity=AlertSeverity.WATCH,
                        location=loc.name,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        headline=f"Sustained Wind Speed {curr.wind_speed} m/s (~{round(curr.wind_speed*3.6)} km/h)",
                        description="Observed surface wind velocities indicate turbulent gusts and structural resistance.",
                        recommendation="Secure loose terrace objects, signage, and lightweight scaffolding.",
                        is_official=False,
                        source="WeatherGPT Algorithmic Impact Engine (Rule-based Threshold)",
                    )
                )

            # Evaluate thunderstorm condition
            cond_lower = curr.condition.lower()
            if "thunder" in cond_lower or "storm" in cond_lower:
                system_risks.append(
                    AlertItem(
                        id=f"sys-storm-{int(datetime.utcnow().timestamp())}",
                        event="Convective Thunderstorm Indicator",
                        category=AlertCategory.THUNDERSTORM,
                        severity=AlertSeverity.WARNING,
                        location=loc.name,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        headline="Convective Lightning & Downburst Activity Observed",
                        description=f"Current meteorological condition reported as '{curr.condition}'. Risk of cloud-to-ground electrical discharge.",
                        recommendation="Take immediate indoor shelter. Disconnect sensitive electronic appliances.",
                        is_official=False,
                        source="WeatherGPT Algorithmic Impact Engine (Rule-based Threshold)",
                    )
                )
        except Exception as e:
            logger.warning(f"Error calculating system risks: {e}")

        total = len(official_alerts) + len(system_risks)

        return AlertsResponse(
            location=city or "Chennai",
            total_active=total,
            official_alerts=official_alerts,
            system_risks=system_risks,
            source="India Meteorological Department (IMD) Feed & WeatherGPT Risk Engine"
        )


alert_service = AlertService()
