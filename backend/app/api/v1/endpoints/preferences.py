from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.session import get_db
from app.models.models import UserPreference
from app.services.advisory_service import advisory_engine, DomainAdvisoryResponse
from app.services.weather_service import weather_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class UserPreferenceSchema(BaseModel):
    session_id: Optional[str] = None
    persona: str = Field(default="general", description="farmer, fisherman, traveler, construction, aviation, events, general")
    default_city: str = Field(default="Chennai")
    language: str = Field(default="en", description="en, hi, ta")
    units: str = Field(default="metric")
    alert_notifications_enabled: bool = True
    voice_enabled: bool = True


@router.get("/", response_model=UserPreferenceSchema)
async def get_preferences(
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Retrieve saved user personalization preferences by session ID or default."""
    if session_id:
        pref = db.query(UserPreference).filter(UserPreference.session_id == session_id).first()
        if pref:
            return UserPreferenceSchema(
                session_id=pref.session_id,
                persona=pref.persona or "general",
                default_city=pref.default_city or "Chennai",
                language=pref.language or "en",
                units=pref.units or "metric",
                alert_notifications_enabled=pref.alert_notifications_enabled,
                voice_enabled=pref.voice_enabled,
            )

    return UserPreferenceSchema(
        session_id=session_id or "anonymous",
        persona="general",
        default_city="Chennai",
        language="en",
        units="metric",
        alert_notifications_enabled=True,
        voice_enabled=True,
    )


@router.post("/", response_model=UserPreferenceSchema)
async def update_preferences(
    pref_in: UserPreferenceSchema,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Update or persist user personalization preferences without requiring mandatory login."""
    target_session = pref_in.session_id or session_id or "default_guest"
    pref = db.query(UserPreference).filter(UserPreference.session_id == target_session).first()

    if not pref:
        pref = UserPreference(
            session_id=target_session,
            persona=pref_in.persona,
            default_city=pref_in.default_city,
            language=pref_in.language,
            units=pref_in.units,
            alert_notifications_enabled=pref_in.alert_notifications_enabled,
            voice_enabled=pref_in.voice_enabled,
        )
        db.add(pref)
    else:
        pref.persona = pref_in.persona
        pref.default_city = pref_in.default_city
        pref.language = pref_in.language
        pref.units = pref_in.units
        pref.alert_notifications_enabled = pref_in.alert_notifications_enabled
        pref.voice_enabled = pref_in.voice_enabled

    db.commit()
    db.refresh(pref)

    return UserPreferenceSchema(
        session_id=pref.session_id,
        persona=pref.persona,
        default_city=pref.default_city,
        language=pref.language,
        units=pref.units,
        alert_notifications_enabled=pref.alert_notifications_enabled,
        voice_enabled=pref.voice_enabled,
    )


@router.get("/advisory", response_model=DomainAdvisoryResponse)
async def get_personalized_advisory(
    persona: Optional[str] = "general",
    city: Optional[str] = "Chennai",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
):
    """
    Computes domain-specialized advisory for the requested persona against current meteorological telemetry.
    Strictly displays WeatherGPT decision-support disclaimer.
    """
    try:
        current_data = await weather_service.get_current_weather(city=city, lat=lat, lon=lon)
        c = current_data.current
        return advisory_engine.evaluate(
            persona=persona or "general",
            city=current_data.location.name,
            temp=c.temperature,
            humidity=c.humidity,
            wind_speed=c.wind_speed,
            precip_mm=c.precipitation_mm or 0.0,
            visibility=c.visibility,
            condition=c.condition,
        )
    except Exception as ex:
        logger.error(f"Error computing personalized advisory: {ex}")
        raise HTTPException(status_code=500, detail=f"Advisory generation error: {str(ex)}")
