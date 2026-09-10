from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IngestionResult(BaseModel):
    """Result structure of an ingestion run."""
    job_name: str
    provider: str
    success: bool
    status: str
    records_ingested: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Any] = None


class BaseIngestor(ABC):
    """
    Abstract Base Class for meteorological ingestion workers.
    Enforces timeout, exponential backoff retry, validation, structured logging,
    and isolated failure tolerance.
    """

    def __init__(
        self,
        name: str,
        provider: str,
        timeout_seconds: float = 12.0,
        max_retries: int = 2,
        backoff_factor: float = 1.5,
    ):
        self.name = name
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @abstractmethod
    async def fetch_and_parse(self, **kwargs) -> Any:
        """Subclasses must implement actual retrieval and parsing logic."""
        pass

    async def run(self, **kwargs) -> IngestionResult:
        """
        Executes ingestion with timeout, retry, and fault containment.
        Never allows unhandled exceptions to crash caller.
        """
        start_time = asyncio.get_event_loop().time()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            try:
                logger.info(f"[{self.name}] Ingestion attempt {attempt}/{self.max_retries + 1}")
                data = await asyncio.wait_for(
                    self.fetch_and_parse(**kwargs),
                    timeout=self.timeout_seconds,
                )
                end_time = asyncio.get_event_loop().time()
                elapsed_ms = round((end_time - start_time) * 1000, 2)

                count = len(data) if isinstance(data, list) else (1 if data is not None else 0)
                logger.info(f"[{self.name}] Ingestion succeeded: {count} records in {elapsed_ms}ms")

                return IngestionResult(
                    job_name=self.name,
                    provider=self.provider,
                    success=True,
                    status="SUCCESS",
                    records_ingested=count,
                    execution_time_ms=elapsed_ms,
                    data=data,
                )
            except asyncio.TimeoutError as te:
                last_error = te
                logger.warning(f"[{self.name}] Attempt {attempt} timed out after {self.timeout_seconds}s")
            except Exception as ex:
                last_error = ex
                logger.warning(f"[{self.name}] Attempt {attempt} failed: {ex}")

            if attempt <= self.max_retries:
                delay = (self.backoff_factor ** attempt)
                logger.info(f"[{self.name}] Backing off for {delay:.2f}s before retry...")
                await asyncio.sleep(delay)

        end_time = asyncio.get_event_loop().time()
        elapsed_ms = round((end_time - start_time) * 1000, 2)
        err_msg = str(last_error) if last_error else "Unknown error during ingestion"
        logger.error(f"[{self.name}] Ingestion failed after {self.max_retries + 1} attempts: {err_msg}")

        return IngestionResult(
            job_name=self.name,
            provider=self.provider,
            success=False,
            status=f"FAILED: {err_msg}",
            records_ingested=0,
            errors=[err_msg],
            execution_time_ms=elapsed_ms,
            data=None,
        )
