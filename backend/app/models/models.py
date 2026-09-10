from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    preferences = relationship("UserPreference", back_populates="user", uselist=False)


class UserPreference(Base):
    """
    Lightweight, non-invasive user personalization model.
    Supports session-based anonymous usage as well as authenticated users.
    """
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), index=True, nullable=True)
    
    # 7 Supported Personas: farmer, fisherman, traveler, construction, aviation, events, general
    persona = Column(String(50), default="general", index=True)
    default_city = Column(String(100), default="Chennai", index=True)
    language = Column(String(10), default="en")  # en, hi, ta
    units = Column(String(10), default="metric")
    preferred_activities = Column(JSON, default=list)
    alert_notifications_enabled = Column(Boolean, default=True)
    high_contrast = Column(Boolean, default=False)
    voice_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), index=True, nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="IN")
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    observations = relationship("WeatherObservation", back_populates="location")

    __table_args__ = (
        Index("idx_location_lat_lon", "latitude", "longitude"),
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location_name = Column(String(150), index=True)
    temperature = Column(Float, nullable=False)
    feels_like = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=False)
    wind_deg = Column(Float, nullable=True)
    visibility = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    condition = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    source = Column(String(100), nullable=False)
    observed_at = Column(DateTime, default=datetime.utcnow, index=True)

    location = relationship("Location", back_populates="observations")

    __table_args__ = (
        Index("idx_obs_location_observed", "location_name", "observed_at"),
    )


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(150), index=True, nullable=False)
    forecast_time = Column(DateTime, nullable=False, index=True)
    temperature_min = Column(Float, nullable=True)
    temperature_max = Column(Float, nullable=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=False)
    pop = Column(Float, default=0.0)  # Probability of precipitation (0.0 - 1.0)
    condition = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_fc_location_time", "location_name", "forecast_time"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    event = Column(String(200), nullable=False)  # e.g., Heavy Rainfall, Cyclone, Heatwave
    severity = Column(String(50), nullable=False)  # Warning, Watch, Advisory, Severe
    sender_name = Column(String(150), nullable=False)  # e.g., India Meteorological Department (IMD)
    headline = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    instruction = Column(Text, nullable=True)
    location_name = Column(String(150), index=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    onset = Column(DateTime, nullable=True)
    expires = Column(DateTime, nullable=True)
    is_official = Column(Boolean, default=True, index=True)  # True = official government warning
    source = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_alert_loc_official", "location_name", "is_official"),
    )


class ModelRunRecord(Base):
    """Tracks historical model cycles, runs, and metadata for GFS and WRF."""
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), index=True, nullable=False)  # gfs, wrf, open_meteo
    model_name = Column(String(100), nullable=False)
    cycle = Column(String(50), nullable=True)  # 00Z, 06Z, 12Z, 18Z
    resolution = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False)
    file_reference = Column(String(255), nullable=True)  # path/URI reference; NOT the raw binary
    metadata_json = Column(JSON, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, index=True)


class IngestionStatusRecord(Base):
    """Tracks execution status, timings, and error metrics for ingestion pipeline jobs."""
    __tablename__ = "ingestion_status"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), index=True, nullable=False)
    provider = Column(String(50), index=True, nullable=False)
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED
    records_ingested = Column(Integer, default=0)
    execution_time_ms = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)


class HistoricalWeather(Base):
    __tablename__ = "historical_weather"

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(150), index=True, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)
    avg_temperature = Column(Float, nullable=False)
    max_temperature = Column(Float, nullable=True)
    min_temperature = Column(Float, nullable=True)
    total_rainfall_mm = Column(Float, nullable=True)
    source = Column(String(150), nullable=False)


class WeatherQueryAudit(Base):
    """Audit log for user weather queries and extracted NLU entities."""
    __tablename__ = "weather_query_audits"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    intent = Column(String(100), nullable=True)
    location_used = Column(String(150), index=True, nullable=False)
    target_date = Column(String(50), nullable=True)
    target_time_slot = Column(String(50), nullable=True)
    activity = Column(String(100), nullable=True)
    risk_level = Column(String(50), nullable=True)
    provider = Column(String(100), nullable=True)
    source = Column(String(150), nullable=True)
    is_llm_enhanced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AlertBroadcastAudit(Base):
    """Audit log for disseminated official and emergency warnings."""
    __tablename__ = "alert_broadcast_audits"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(100), index=True, nullable=False)
    event = Column(String(200), nullable=False)
    severity = Column(String(50), nullable=False)
    is_official = Column(Boolean, default=True)
    location = Column(String(150), index=True, nullable=False)
    source = Column(String(150), nullable=False)
    provider = Column(String(100), nullable=True)
    client_count = Column(Integer, default=0)
    broadcast_at = Column(DateTime, default=datetime.utcnow, index=True)


class ClaimVerificationAudit(Base):
    """Audit log for weather claim verification requests."""
    __tablename__ = "claim_verification_audits"

    id = Column(Integer, primary_key=True, index=True)
    claim_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)  # VERIFIED, UNVERIFIED, CONTRADICTED
    city = Column(String(150), index=True, nullable=False)
    confidence = Column(Float, nullable=False)
    official_warning_checked = Column(Boolean, default=False)
    source_attribution = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
