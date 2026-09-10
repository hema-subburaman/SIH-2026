from typing import Dict, Any, List
import asyncio
import logging
from datetime import datetime, timezone
from app.ingestion.base_ingestor import IngestionResult
from app.ingestion.gfs_ingestor import GFSIngestor
from app.ingestion.wrf_ingestor import WRFIngestor
from app.ingestion.weather_ingestor import WeatherIngestor
from app.ingestion.alert_ingestor import AlertIngestor

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """
    Orchestration Scheduler for meteorological ingestion pipeline.
    Executes multiple provider workers with isolated fault tolerance.
    """

    def __init__(self):
        self.gfs_worker = GFSIngestor()
        self.wrf_worker = WRFIngestor()
        self.weather_worker = WeatherIngestor()
        self.alert_worker = AlertIngestor()
        self.last_run_results: Dict[str, IngestionResult] = {}
        self.last_run_timestamp: Optional[str] = None

    async def run_all(
        self, city: str = "Chennai", lat: float = 13.0827, lon: float = 80.2707
    ) -> Dict[str, IngestionResult]:
        """
        Executes ingestion workers in parallel with complete fault isolation.
        Failure in any individual ingestor does not prevent other workers from succeeding.
        """
        logger.info(f"Starting ingestion pipeline cycle for {city} ({lat}, {lon})")

        tasks = [
            self.weather_worker.run(city=city, lat=lat, lon=lon),
            self.alert_worker.run(city=city, lat=lat, lon=lon),
            self.gfs_worker.run(lat=lat, lon=lon, days=5),
            self.wrf_worker.run(lat=lat, lon=lon, days=3),
        ]

        # Use return_exceptions=True to guarantee no exception escapes
        results = await asyncio.gather(*tasks, return_exceptions=True)

        worker_names = ["weather", "alerts", "gfs", "wrf"]
        output: Dict[str, IngestionResult] = {}

        for name, res in zip(worker_names, results):
            if isinstance(res, IngestionResult):
                output[name] = res
            else:
                output[name] = IngestionResult(
                    job_name=name,
                    provider=name,
                    success=False,
                    status=f"FAILED: {str(res)}",
                    errors=[str(res)],
                )

        self.last_run_results = output
        self.last_run_timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"Ingestion pipeline completed. Summary: " + ", ".join([f"{k}:{v.status}" for k, v in output.items()]))
        return output

    def get_status(self) -> Dict[str, Any]:
        """Returns the latest execution status of all ingestion jobs."""
        return {
            "last_run": self.last_run_timestamp,
            "jobs": {
                name: {
                    "job_name": res.job_name,
                    "provider": res.provider,
                    "success": res.success,
                    "status": res.status,
                    "records_ingested": res.records_ingested,
                    "execution_time_ms": res.execution_time_ms,
                    "timestamp": res.timestamp.isoformat(),
                    "errors": res.errors,
                }
                for name, res in self.last_run_results.items()
            },
        }


ingestion_scheduler = IngestionScheduler()
