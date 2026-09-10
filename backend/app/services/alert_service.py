from typing import List, Optional, Dict, Any, Set
from fastapi import WebSocket
from datetime import datetime, timezone
import asyncio
from app.providers.imd_warning_provider import OfficialMeteorologicalWarningProvider
from app.services.weather_service import weather_service
from app.schemas.alert import AlertItem, AlertCategory, AlertSeverity, AlertsResponse
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class AlertService:
    """
    Disaster Early Warning & Alerts Service.
    Coordinates official CAP bulletin ingestion from IMD / NDMA,
    evaluates algorithmic sensor thresholds, and disseminates real-time alerts
    via WebSockets with deduplication and background polling.
    """

    def __init__(self):
        self.official_provider = OfficialMeteorologicalWarningProvider()
        # Active websocket connections for live alert dissemination
        self.active_connections: Set[WebSocket] = set()
        # Set of seen alert IDs to prevent duplicate broadcasts
        self.seen_alert_ids: Set[str] = set()
        self._polling_task: Optional[asyncio.Task] = None
        self._is_polling = False

    async def register_ws(self, websocket: WebSocket):
        """Registers an already-accepted WebSocket connection."""
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client registered. Total active: {len(self.active_connections)}")

    async def connect_ws(self, websocket: WebSocket):
        """Accepts and registers a new WebSocket connection."""
        await websocket.accept()
        await self.register_ws(websocket)

    def disconnect_ws(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast_alert(self, alert_payload: Dict[str, Any]):
        """Broadcasts structured alert payload to all connected clients."""
        if not self.active_connections:
            return

        message = json.dumps(alert_payload)
        for conn in list(self.active_connections):
            try:
                await conn.send_text(message)
            except Exception:
                self.disconnect_ws(conn)

    async def poll_and_broadcast_new_alerts(self) -> List[AlertItem]:
        """
        Polls official warning feeds for monitored cities, detects newly issued or
        changed alerts, suppresses duplicates, and broadcasts via WebSocket.
        """
        new_alerts: List[AlertItem] = []
        cities_to_check = settings.MONITORED_ALERT_CITIES or ["Chennai", "Bengaluru", "Mumbai", "Delhi"]

        for city_name in cities_to_check:
            try:
                alerts, coverage_avail, _ = await self.official_provider.get_alerts_with_coverage(city=city_name)
                if not coverage_avail:
                    continue

                for alert in alerts:
                    # Deduplication key: combination of id, event, and severity
                    dedup_key = f"{alert.id}:{alert.event}:{alert.severity}"
                    if dedup_key not in self.seen_alert_ids:
                        self.seen_alert_ids.add(dedup_key)
                        new_alerts.append(alert)
                        logger.info(f"New official warning detected: {alert.event} ({alert.location})")

                        # Broadcast to active WebSocket clients
                        broadcast_payload = {
                            "type": "OFFICIAL_WARNING_ALERT",
                            "alert": alert.model_dump(),
                            "broadcast_at": datetime.now(timezone.utc).isoformat(),
                            "is_official": True,
                        }
                        await self.broadcast_alert(broadcast_payload)

                        # Audit logging if available
                        try:
                            from app.services.audit_service import audit_service
                            await audit_service.log_alert_broadcast(alert, len(self.active_connections))
                        except Exception as e:
                            logger.debug(f"Audit log skipped for alert: {e}")

            except Exception as e:
                logger.warning(f"Error polling official alerts for {city_name}: {e}")

        return new_alerts

    async def start_alert_polling_loop(self):
        """Background worker running periodic alert polling at configurable intervals."""
        self._is_polling = True
        interval = max(30, settings.ALERT_POLL_INTERVAL_SECONDS)
        # Yield to event loop immediately on startup before initial poll
        # to ensure server finishes ASGI startup and is ready for client connections
        try:
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            return

        logger.info(f"Background official alert polling worker started with interval: {interval}s")

        while self._is_polling:
            try:
                await self.poll_and_broadcast_new_alerts()
            except Exception as e:
                logger.error(f"Unexpected error in alert polling loop: {e}")

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    def stop_alert_polling_loop(self):
        self._is_polling = False
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()

    async def get_alerts_for_location(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> AlertsResponse:
        # 1. Fetch Official Warnings from IMD / Warning Feed with clean location resolution
        official_alerts, coverage_avail, resolved_state = await self.official_provider.get_alerts_with_coverage(
            city=city, lat=lat, lon=lon
        )

        coverage_notice = None
        if not coverage_avail:
            coverage_notice = (
                f"Official government warning coverage is unavailable for '{city}'. "
                "IMD / NDMA bulletins are tracked for recognized Indian cities and states."
            )

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
                        id=f"sys-heat-{int(datetime.now(timezone.utc).timestamp())}",
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
                        provider="WeatherGPT Risk Engine",
                        data_type="algorithmic_risk",
                    )
                )

            # Evaluate gale wind
            if curr.wind_speed >= settings.WIND_GALE_MIN:
                system_risks.append(
                    AlertItem(
                        id=f"sys-wind-{int(datetime.now(timezone.utc).timestamp())}",
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
                        provider="WeatherGPT Risk Engine",
                        data_type="algorithmic_risk",
                    )
                )

            # Evaluate thunderstorm condition
            cond_lower = curr.condition.lower()
            if "thunder" in cond_lower or "storm" in cond_lower:
                system_risks.append(
                    AlertItem(
                        id=f"sys-storm-{int(datetime.now(timezone.utc).timestamp())}",
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
                        provider="WeatherGPT Risk Engine",
                        data_type="algorithmic_risk",
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
            source="India Meteorological Department (IMD) Feed & WeatherGPT Risk Engine",
            provider="IMD / WeatherGPT Hybrid",
            official_coverage_available=coverage_avail,
            coverage_notice=coverage_notice
        )


alert_service = AlertService()

