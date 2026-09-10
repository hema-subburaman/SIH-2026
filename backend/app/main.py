from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import settings
from app.api.v1.api import api_router
from app.database.session import engine, Base, init_and_migrate_db
from app.services.alert_service import alert_service
# Import models to ensure tables are registered with Base.metadata
import app.models.models

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("weathergpt")

# Create and auto-migrate database tables automatically
try:
    init_and_migrate_db()
    logger.info("Database initialized and migrated successfully.")
except Exception as e:
    logger.warning(f"Database initialization notice: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background alert polling worker
    polling_task = asyncio.create_task(alert_service.start_alert_polling_loop())
    alert_service._polling_task = polling_task
    logger.info("Alert polling background service spawned.")
    yield
    # Shutdown: Stop polling worker cleanly
    alert_service.stop_alert_polling_loop()
    logger.info("Alert polling background service shutdown.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "database": "connected"
    }


import json


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """WebSocket endpoint broadcasting real-time extreme weather alerts to connected clients."""
    await websocket.accept()
    await alert_service.register_ws(websocket)
    try:
        while True:
            # Keep-alive ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                try:
                    payload = json.loads(data)
                    if isinstance(payload, dict) and payload.get("type") == "ping":
                        await websocket.send_text("pong")
                except Exception:
                    pass
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected cleanly via WebSocketDisconnect.")
    except Exception as e:
        logger.info(f"WebSocket client connection closed: {e}")
    finally:
        alert_service.disconnect_ws(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
