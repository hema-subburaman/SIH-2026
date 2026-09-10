from fastapi import APIRouter
from app.api.v1.endpoints import weather, risk, alerts, climate, claim, chat, providers

api_router = APIRouter()

api_router.include_router(weather.router, prefix="/weather", tags=["Weather"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk & Decision Support"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts & Early Warnings"])
api_router.include_router(climate.router, prefix="/climate", tags=["Climate Trends"])
api_router.include_router(claim.router, prefix="/claim", tags=["Claim Verification"])
api_router.include_router(chat.router, prefix="/chat", tags=["Conversational AI"])
api_router.include_router(providers.router, prefix="/providers", tags=["Providers & NWP"])
