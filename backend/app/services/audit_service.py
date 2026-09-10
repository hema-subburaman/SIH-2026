import logging
from typing import Optional, Dict, Any
from app.database.session import SessionLocal
from app.models.models import WeatherQueryAudit, AlertBroadcastAudit, ClaimVerificationAudit
from app.schemas.chat import ChatQueryResponse
from app.schemas.alert import AlertItem
from app.schemas.claim import ClaimVerifyResponse

logger = logging.getLogger(__name__)


class AuditService:
    """
    Lightweight, resilient persistence service for auditability and compliance.
    Logs queries, official alert broadcasts, and claim verification telemetry without
    blocking core request paths or leaking API keys.
    """

    async def log_weather_query(self, response: ChatQueryResponse):
        """Asynchronously records a user weather query and its classification metadata."""
        try:
            db = SessionLocal()
            try:
                summary = response.weather_summary or {}
                audit = WeatherQueryAudit(
                    query=response.query,
                    language=response.language,
                    intent=response.intent,
                    location_used=response.location_used,
                    target_date=summary.get("target_date", "today"),
                    target_time_slot=summary.get("target_time_slot", "now"),
                    activity=summary.get("activity"),
                    risk_level=response.risk_level.value if response.risk_level else None,
                    provider=response.provider or "WeatherGPT Orchestrator",
                    source=response.source,
                    is_llm_enhanced=response.is_llm_enhanced
                )
                db.add(audit)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Audit log notice (non-fatal): {e}")

    async def log_alert_broadcast(self, alert: AlertItem, client_count: int):
        """Records an official alert dissemination event."""
        try:
            db = SessionLocal()
            try:
                audit = AlertBroadcastAudit(
                    alert_id=alert.id,
                    event=alert.event,
                    severity=alert.severity.value,
                    is_official=alert.is_official,
                    location=alert.location,
                    source=alert.source,
                    provider=alert.provider or "IMD",
                    client_count=client_count
                )
                db.add(audit)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Alert audit log notice (non-fatal): {e}")

    async def log_claim_verification(self, claim_text: str, city: str, result: ClaimVerifyResponse):
        """Records a fact-check claim verification event."""
        try:
            db = SessionLocal()
            try:
                audit = ClaimVerificationAudit(
                    claim_text=claim_text,
                    status=result.status.value,
                    city=city,
                    confidence=result.confidence,
                    official_warning_checked=result.official_warning_checked,
                    source_attribution=result.source_attribution
                )
                db.add(audit)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Claim verification audit notice (non-fatal): {e}")


audit_service = AuditService()
