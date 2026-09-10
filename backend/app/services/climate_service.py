from typing import Optional
from app.providers.open_meteo import OpenMeteoProvider
from app.schemas.climate import ClimateTrendResponse


class ClimateService:
    def __init__(self):
        self.provider = OpenMeteoProvider()

    async def get_historical_trends(
        self,
        city: Optional[str] = "Chennai",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        years: int = 10
    ) -> ClimateTrendResponse:
        return await self.provider.get_climate_history(city=city, lat=lat, lon=lon, years=years)


climate_service = ClimateService()
