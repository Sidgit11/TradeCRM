from typing import Optional

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import get_logger, setup_logging
from app.websocket.manager import ws_manager

# Import routers
from app.api.auth import router as auth_router, tenant_router
from app.api.contacts import router as contacts_router, list_router as contact_list_router
from app.api.companies import router as companies_router
from app.api.webhooks import router as webhooks_router
from app.api.agents import router as agents_router
from app.api.discover import router as discover_router
from app.api.enrichment import router as enrichment_router
from app.api.campaigns import router as campaigns_router
from app.api.inbox import router as inbox_router
from app.api.pipeline import router as pipeline_router
from app.api.dashboard import router as dashboard_router
from app.api.billing import router as billing_router
from app.api.clerk_webhook import router as clerk_webhook_router
from app.api.admin import router as admin_router
from app.api.catalog import router as catalog_router
from app.api.email import router as email_router
from app.api.leads import router as leads_router
from app.api.whatsapp import router as whatsapp_router
from app.api.templates import router as templates_router
from app.api.shipments import router as shipments_router
from app.api.interests import router as interests_router
from app.api.insights import router as insights_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Tradyon Outreach API starting up")
    logger.info("CORS allowed origin: %s", settings.FRONTEND_URL)
    yield
    logger.info("Tradyon Outreach API shutting down")


app = FastAPI(
    title="Tradyon Outreach API",
    description="AI-powered multi-channel outreach platform for commodity traders",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(tenant_router)
app.include_router(contacts_router)
app.include_router(contact_list_router)
app.include_router(companies_router)
app.include_router(webhooks_router)
app.include_router(agents_router)
app.include_router(discover_router)
app.include_router(enrichment_router)
app.include_router(campaigns_router)
app.include_router(inbox_router)
app.include_router(pipeline_router)
app.include_router(dashboard_router)
app.include_router(billing_router)
app.include_router(clerk_webhook_router)
app.include_router(admin_router)
app.include_router(catalog_router)
app.include_router(email_router)
app.include_router(leads_router)
app.include_router(templates_router)
app.include_router(shipments_router)
app.include_router(interests_router)
app.include_router(insights_router)
app.include_router(whatsapp_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
):
    if not tenant_id or not user_id:
        logger.warning("WebSocket connection rejected: missing tenant_id or user_id")
        await websocket.close(code=4001)
        return

    conn_id = await ws_manager.connect(websocket, tenant_id, user_id)
    logger.info("WebSocket connected: conn=%s tenant=%s user=%s", conn_id[:8], tenant_id, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(conn_id)
        logger.info("WebSocket disconnected: conn=%s", conn_id[:8])
