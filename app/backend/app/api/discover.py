"""Discovery API — Buyer discovery using TradeGenie + Research Agent."""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.company import Company
from app.models.enums import CompanySource, EnrichmentStatus, AgentTaskType, AgentTaskStatus
from app.models.activity import AgentTask
from app.agents.research_agent import research_agent

logger = get_logger("api.discover")
router = APIRouter(prefix="/discover", tags=["discover"])


class DiscoverSearchRequest(BaseModel):
    query: str
    country: Optional[str] = None
    commodity: Optional[str] = None


class DiscoverSaveRequest(BaseModel):
    company_name: str
    country: Optional[str] = None
    website: Optional[str] = None
    commodities: list = []
    import_volume_annual: Optional[float] = None
    confidence_score: Optional[float] = None
    add_to_pipeline: bool = False


class DiscoverResultItem(BaseModel):
    name: str
    country: Optional[str] = None
    commodities: list = []
    import_volume: Optional[float] = None
    shipment_frequency: Optional[str] = None
    confidence: Optional[float] = None
    source: str = "discovery"


@router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def search_buyers(
    body: DiscoverSearchRequest,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for buyers using AI-powered discovery.
    Returns an agent_task_id for tracking progress via WebSocket.
    """
    logger.info("Discovery search: query='%s' country=%s tenant=%s", body.query, body.country, tenant_id)

    # Create agent task
    task = AgentTask(
        tenant_id=tenant_id,
        task_type=AgentTaskType.buyer_discovery,
        status=AgentTaskStatus.pending,
        input_data={
            "query": body.query,
            "country": body.country,
            "commodity": body.commodity,
        },
        steps=[
            {"name": "Searching shipment databases", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Analyzing import records", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Identifying unique importers", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Ranking by volume and recency", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
        ],
        current_step_index=0,
        created_by=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # TODO: dispatch to Celery for async execution
    # For now return the task_id so frontend can poll

    return {
        "agent_task_id": str(task.id),
        "status": "pending",
        "message": "Discovery search queued. Track progress via WebSocket or poll /agents/tasks/{id}.",
    }


@router.post("/save", status_code=status.HTTP_201_CREATED)
async def save_discovered_company(
    body: DiscoverSaveRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Save a discovered company to the companies table."""
    # Check for existing company with same name in tenant
    existing = await db.execute(
        select(Company).where(
            Company.tenant_id == tenant_id,
            Company.name == body.company_name,
            Company.is_deleted.is_(False),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company with this name already exists",
        )

    company = Company(
        tenant_id=tenant_id,
        name=body.company_name,
        country=body.country,
        website=body.website,
        commodities=body.commodities,
        import_volume_annual=body.import_volume_annual,
        confidence_score=body.confidence_score,
        source=CompanySource.discovery,
        enrichment_status=EnrichmentStatus.not_enriched,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)

    logger.info("Discovered company saved: id=%s name=%s tenant=%s", company.id, company.name, tenant_id)

    return {
        "id": str(company.id),
        "name": company.name,
        "status": "saved",
    }
