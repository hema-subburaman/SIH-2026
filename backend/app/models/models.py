from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
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
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    default_city = Column(String(100), default="Chennai")
    language = Column(String(10), default="en")  # en, hi, ta
    units = Column(String(10), default="metric")
    high_contrast = Column(Boolean, default=False)
    voice_enabled = Column(Boolean, default=True)

    user = relationship("User", back_populates="preferences")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), index=True, nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="IN")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    observations = relationship("WeatherObservation", back_populates="location")


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
    observed_at = Column(DateTime, default=datetime.utcnow)

    location = relationship("Location", back_populates="observations")


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
    is_official = Column(Boolean, default=True)  # True = official government warning
    source = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)


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
    broadcast_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)
