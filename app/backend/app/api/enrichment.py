"""Enrichment API — Company profiling and contact discovery."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.company import Company
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.models.enums import (
    AgentTaskStatus,
    AgentTaskType,
    EnrichmentStatus,
    ContactEnrichmentStatus,
)
from app.models.activity import AgentTask
from app.services.enrichment_service import run_enrichment_pipeline

logger = get_logger("api.enrichment")
router = APIRouter(prefix="/companies", tags=["enrichment"])

# Plan enrichment limits (mirrors billing.py)
_PLAN_ENRICHMENT_LIMITS = {
    "free_trial": 10,
    "starter": 100,
    "growth": 500,
    "pro": -1,  # unlimited
}


@router.post("/{company_id}/research", status_code=status.HTTP_202_ACCEPTED)
async def research_company(
    company_id: uuid.UUID,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI research on a company. Returns agent_task_id for tracking."""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant_id,
            Company.is_deleted.is_(False),
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Mark as enriching
    company.enrichment_status = EnrichmentStatus.enriching
    await db.flush()

    # Create agent task
    task = AgentTask(
        tenant_id=tenant_id,
        task_type=AgentTaskType.company_research,
        status=AgentTaskStatus.pending,
        input_data={
            "company_id": str(company_id),
            "company_name": company.name,
            "country": company.country,
            "website": company.website,
        },
        steps=[
            {"name": "Searching web for company info", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Analyzing shipment data", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Scraping company website", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Checking trade directories", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Synthesizing profile", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
        ],
        current_step_index=0,
        created_by=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(
        "Company research queued: company=%s task=%s tenant=%s",
        company.name, task.id, tenant_id,
    )

    return {
        "agent_task_id": str(task.id),
        "company_id": str(company_id),
        "status": "enriching",
    }


@router.post("/{company_id}/enrich", status_code=status.HTTP_202_ACCEPTED)
async def enrich_company(
    company_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger full company enrichment pipeline (Perplexity + Firecrawl + Gemini + Apollo).
    Returns immediately with agent_task_id for progress tracking.
    """
    # --- Check enrichment credit balance ---
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )).scalar_one()

    plan = tenant.plan.value
    limit = _PLAN_ENRICHMENT_LIMITS.get(plan, 10)

    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )
    enrichments_used = (await db.execute(
        select(func.count()).where(
            AgentTask.tenant_id == tenant_id,
            AgentTask.task_type == AgentTaskType.company_research,
            AgentTask.created_at >= month_start,
        )
    )).scalar() or 0

    if limit != -1:
        if enrichments_used >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Enrichment limit reached ({enrichments_used}/{limit} this month). Upgrade your plan for more.",
            )

    # --- Load company ---
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant_id,
            Company.is_deleted.is_(False),
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Reject if already enriching
    if company.enrichment_status == EnrichmentStatus.enriching:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Enrichment already in progress for this company",
        )

    # --- Check API keys are configured ---
    missing_keys = []
    if not settings.PERPLEXITY_API_KEY:
        missing_keys.append("PERPLEXITY_API_KEY")
    if not settings.FIRECRAWL_API_KEY:
        missing_keys.append("FIRECRAWL_API_KEY")
    if not settings.APOLLO_API_KEY:
        missing_keys.append("APOLLO_API_KEY")
    if not settings.GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    if missing_keys:
        logger.error("Enrichment API keys not configured: %s", missing_keys)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enrichment service not configured. Contact support.",
        )

    # --- Mark as enriching ---
    company.enrichment_status = EnrichmentStatus.enriching
    await db.flush()

    # --- Create AgentTask with 5 steps ---
    task = AgentTask(
        tenant_id=tenant_id,
        task_type=AgentTaskType.company_research,
        status=AgentTaskStatus.pending,
        input_data={
            "company_id": str(company_id),
            "company_name": company.name,
            "country": company.country,
            "website": company.website,
        },
        steps=[
            {"name": "Searching the web for company info", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Scraping website & checking trade directories", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Analyzing company data with AI", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Discovering decision makers & contacts", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Finalizing company profile", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
        ],
        current_step_index=0,
        created_by=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(
        "Company enrichment triggered: company=%s task=%s tenant=%s",
        company.name, task.id, tenant_id,
    )

    # --- Launch background pipeline ---
    background_tasks.add_task(
        run_enrichment_pipeline,
        company_id=company_id,
        task_id=task.id,
        tenant_id=tenant_id,
    )

    # Calculate remaining enrichments
    if limit == -1:
        remaining = 999999
    else:
        # enrichments_used was computed above; +1 for the one we just created
        remaining = max(0, limit - (enrichments_used + 1))

    return {
        "agent_task_id": str(task.id),
        "company_id": str(company_id),
        "status": "enriching",
        "steps": task.steps,
        "enrichments_remaining": remaining,
    }


@router.get("/{company_id}/enrich/status")
async def get_enrichment_status(
    company_id: uuid.UUID,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get the current enrichment status and step progress for a company."""
    # Verify company exists and belongs to tenant
    company_result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant_id,
            Company.is_deleted.is_(False),
        )
    )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Find the most recent enrichment task for this company
    task_result = await db.execute(
        select(AgentTask).where(
            AgentTask.tenant_id == tenant_id,
            AgentTask.task_type == AgentTaskType.company_research,
            AgentTask.input_data["company_id"].as_string() == str(company_id),
        ).order_by(AgentTask.created_at.desc()).limit(1)
    )
    task = task_result.scalar_one_or_none()

    if not task:
        return {
            "company_id": str(company_id),
            "enrichment_status": company.enrichment_status.value,
            "agent_task": None,
        }

    return {
        "company_id": str(company_id),
        "enrichment_status": company.enrichment_status.value,
        "agent_task": {
            "id": str(task.id),
            "status": task.status.value,
            "steps": task.steps,
            "current_step_index": task.current_step_index,
            "credits_consumed": task.credits_consumed,
            "output_data": task.output_data,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
    }


@router.post("/{company_id}/find-contacts", status_code=status.HTTP_202_ACCEPTED)
async def find_company_contacts(
    company_id: uuid.UUID,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Trigger contact discovery for a company. Returns agent_task_id."""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant_id,
            Company.is_deleted.is_(False),
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    task = AgentTask(
        tenant_id=tenant_id,
        task_type=AgentTaskType.contact_enrichment,
        status=AgentTaskStatus.pending,
        input_data={
            "company_id": str(company_id),
            "company_name": company.name,
            "country": company.country,
            "website": company.website,
        },
        steps=[
            {"name": "Searching for decision makers", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Identifying relevant roles", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Verifying contact details", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Checking WhatsApp availability", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
        ],
        current_step_index=0,
        created_by=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(
        "Contact discovery queued: company=%s task=%s tenant=%s",
        company.name, task.id, tenant_id,
    )

    return {
        "agent_task_id": str(task.id),
        "company_id": str(company_id),
        "status": "searching",
    }


@router.post("/{contact_id}/enrich", status_code=status.HTTP_202_ACCEPTED, tags=["contacts"])
async def enrich_contact(
    contact_id: uuid.UUID,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Trigger enrichment on a single contact (verify email, find phone)."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
            Contact.is_deleted.is_(False),
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.enrichment_status = ContactEnrichmentStatus.enriching
    await db.flush()

    task = AgentTask(
        tenant_id=tenant_id,
        task_type=AgentTaskType.contact_enrichment,
        status=AgentTaskStatus.pending,
        input_data={
            "contact_id": str(contact_id),
            "contact_name": contact.name,
            "contact_email": contact.email,
            "company_name": contact.company_name,
        },
        steps=[
            {"name": "Verifying email address", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Searching for phone number", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
            {"name": "Checking LinkedIn profile", "status": "pending", "detail": None, "started_at": None, "completed_at": None},
        ],
        current_step_index=0,
        created_by=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info("Contact enrichment queued: contact=%s task=%s", contact.name, task.id)

    return {
        "agent_task_id": str(task.id),
        "contact_id": str(contact_id),
        "status": "enriching",
    }
