from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "WeatherGPT"
    PROJECT_DESCRIPTION: str = "Conversational AI Platform for Weather Forecasting, Alerts, Climate Information and Decision Support"
    API_V1_STR: str = "/api/v1"
    
    # Security & Keys
    OPENWEATHER_API_KEY: str = Field(default="", validation_alias="OPENWEATHER_API_KEY")
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    DATABASE_URL: str = Field(default="sqlite:///./weathergpt.db", validation_alias="DATABASE_URL")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    # Weather Impact Engine Configurable Thresholds (Rule-Based Prototype)
    # Heat Index Thresholds (°C)
    HEAT_CAUTION_TEMP: float = 32.0
    HEAT_DANGER_TEMP: float = 40.0
    
    # Wind Speed Thresholds (m/s)
    WIND_BREEZE_MAX: float = 8.0     # ~29 km/h
    WIND_GALE_MIN: float = 14.0      # ~50 km/h
    
    # Rain Probability Thresholds (0-100%)
    RAIN_CHANCE_MED: float = 30.0
    RAIN_CHANCE_HIGH: float = 65.0
    
    # Humidity (%)
    HUMIDITY_HIGH: float = 75.0
    
    # Visibility (meters)
    VISIBILITY_POOR: float = 2000.0
    
    # Alert Polling Configuration
    ALERT_POLL_INTERVAL_SECONDS: int = 300  # Default 5 minutes
    MONITORED_ALERT_CITIES: List[str] = [
        "Chennai", "Bengaluru", "Mumbai", "Delhi", "Kolkata", "Hyderabad"
    ]

    # NWP Models Configuration (GFS & WRF)
    GFS_NWP_ENDPOINT: str = Field(default="", validation_alias="GFS_NWP_ENDPOINT")
    GFS_NOMADS_ENABLED: bool = Field(default=True, validation_alias="GFS_NOMADS_ENABLED")
    GFS_FILE_PATH: str = Field(default="", validation_alias="GFS_FILE_PATH")
    WRF_MODEL_ENDPOINT: str = Field(default="", validation_alias="WRF_MODEL_ENDPOINT")
    WRF_NETCDF_PATH: str = Field(default="", validation_alias="WRF_NETCDF_PATH")
    INGESTION_ENABLED: bool = Field(default=True, validation_alias="INGESTION_ENABLED")
    
    # Model Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
