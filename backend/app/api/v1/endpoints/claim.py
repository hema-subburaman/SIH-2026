from fastapi import APIRouter, HTTPException
from app.schemas.claim import ClaimVerifyRequest, ClaimVerifyResponse
from app.services.claim_verifier import claim_verifier
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/verify", response_model=ClaimVerifyResponse)
async def verify_claim(payload: ClaimVerifyRequest):
    """
    Fact-checks weather claims and rumors against live observations and official warning databases.
    Returns VERIFIED, CONTRADICTED, or UNVERIFIED.
    """
    try:
        data = await claim_verifier.verify_claim(payload)
        return data
    except Exception as e:
        logger.error(f"Error in /claim/verify: {e}")
        raise HTTPException(status_code=500, detail="Claim verification engine failed")
