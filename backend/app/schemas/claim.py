from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ClaimStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"


class ClaimVerifyRequest(BaseModel):
    claim: str = Field(..., description="The user's meteorological statement/claim to check")
    city: Optional[str] = "Chennai"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: Optional[str] = "en"


class ClaimVerifyResponse(BaseModel):
    claim: str
    status: ClaimStatus
    verdict_summary: str
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    evidence_factors: List[str] = []
    official_warning_checked: bool
    source_attribution: str
    disclaimer: str = (
        "Claim verification cross-references current observations, forecast metrics, and official warning databases. "
        "Severe weather warnings require corroboration from authorized government agencies (e.g. IMD)."
    )
