from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.schemas.weather import NormalizedWeatherResponse
from app.schemas.alert import AlertItem


class WeatherProvider(ABC):
    """Abstract interface for retrieving current weather observations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def get_current_weather(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> NormalizedWeatherResponse:
        pass


class ForecastProvider(ABC):
    """Abstract interface for retrieving meteorological forecast data."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def get_forecast(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5
    ) -> NormalizedWeatherResponse:
        pass


class WarningProvider(ABC):
    """Abstract interface for retrieving extreme weather early warnings."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def get_alerts(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> List[AlertItem]:
        pass


class NWPProvider(ABC):
    """Abstract interface for Numerical Weather Prediction (NWP) model outputs (GFS/WRF)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def get_model_run_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_grid_forecast(
        self,
        lat: float,
        lon: float,
        step_hours: int = 3
    ) -> Dict[str, Any]:
        pass


class UpstreamRateLimitError(Exception):
    """Raised when an upstream meteorological provider returns HTTP 429 Too Many Requests."""

    def __init__(
        self,
        message: str = "Upstream weather service is temporarily rate-limited (HTTP 429).",
        retry_after: Optional[int] = None,
        provider: str = "Open-Meteo",
    ):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after
        self.provider = provider

