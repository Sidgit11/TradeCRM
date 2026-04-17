"""Pipeline API — Kanban board, deal tracking, stage management."""
from typing import Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.company import Company
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.models.pipeline import PipelineOpportunity, PipelineStage
from app.models.activity import ActivityLog
from app.models.enums import ActorType, OpportunitySource
from app.schemas.pipeline import (
    OpportunityCreate, OpportunityMoveRequest, OpportunityResponse,
    OpportunityUpdate, PipelineStageResponse, PipelineStats,
)

logger = get_logger("api.pipeline")
router = APIRouter(prefix="/pipeline", tags=["pipeline"])

DEFAULT_STAGES = [
    {"name": "New Lead", "slug": "new_lead", "order": 1, "color": "#93C5FD"},
    {"name": "Contacted", "slug": "contacted", "order": 2, "color": "#C4B5FD"},
    {"name": "In Conversation", "slug": "in_conversation", "order": 3, "color": "#FDE68A"},
    {"name": "Negotiation", "slug": "negotiation", "order": 4, "color": "#FDBA74"},
    {"name": "Sample Sent", "slug": "sample_sent", "order": 5, "color": "#86EFAC"},
    {"name": "Closed Won", "slug": "closed_won", "order": 6, "color": "#22C55E"},
    {"name": "Closed Lost", "slug": "closed_lost", "order": 7, "color": "#FCA5A5"},
]


async def _ensure_default_stages(db: AsyncSession, tenant_id: uuid.UUID) -> list:
    """Create default pipeline stages for a tenant if none exist."""
    result = await db.execute(
        select(PipelineStage).where(PipelineStage.tenant_id == tenant_id)
    )
    stages = list(result.scalars().all())
    if stages:
        return stages

    stages = []
    for s in DEFAULT_STAGES:
        stage = PipelineStage(
            tenant_id=tenant_id, name=s["name"], slug=s["slug"],
            order=s["order"], color=s["color"], is_default=True,
        )
        db.add(stage)
        stages.append(stage)

    await db.commit()
    for s in stages:
        await db.refresh(s)

    logger.info("Default pipeline stages created for tenant=%s", tenant_id)
    return stages


async def _generate_display_id(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    """Generate a human-readable ID like 'TRAD-0001' using first 4 chars of org name."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    prefix = "DEAL"
    if tenant and tenant.company_name:
        # Take first 4 alpha chars, uppercase
        alpha_chars = [c for c in tenant.company_name.upper() if c.isalpha()]
        prefix = "".join(alpha_chars[:4]) if len(alpha_chars) >= 4 else "".join(alpha_chars).ljust(4, "X")

    # Get the max existing sequence number for this tenant
    result = await db.execute(
        select(func.count()).where(PipelineOpportunity.tenant_id == tenant_id)
    )
    count = (result.scalar() or 0) + 1
    return f"{prefix}-{count:04d}"


async def _opp_response(db: AsyncSession, opp: PipelineOpportunity) -> OpportunityResponse:
    company = (await db.execute(select(Company).where(Company.id == opp.company_id))).scalar_one_or_none()
    contact = None
    if opp.contact_id:
        contact = (await db.execute(select(Contact).where(Contact.id == opp.contact_id))).scalar_one_or_none()
    stage = (await db.execute(select(PipelineStage).where(PipelineStage.id == opp.stage_id))).scalar_one_or_none()

    return OpportunityResponse(
        id=str(opp.id), display_id=opp.display_id,
        tenant_id=str(opp.tenant_id),
        title=opp.title,
        company_id=str(opp.company_id),
        company_name=company.name if company else None,
        contact_id=str(opp.contact_id) if opp.contact_id else None,
        contact_name=contact.name if contact else None,
        stage_id=str(opp.stage_id),
        stage_name=stage.name if stage else None,
        stage_color=stage.color if stage else None,
        source=opp.source.value,
        value=float(opp.value) if opp.value else None,
        commodity=opp.commodity,
        quantity_mt=float(opp.quantity_mt) if opp.quantity_mt else None,
        target_price=float(opp.target_price) if opp.target_price else None,
        our_price=float(opp.our_price) if opp.our_price else None,
        competitor_price=float(opp.competitor_price) if opp.competitor_price else None,
        estimated_value_usd=float(opp.estimated_value_usd) if opp.estimated_value_usd else None,
        incoterms=opp.incoterms, payment_terms=opp.payment_terms,
        container_type=opp.container_type,
        number_of_containers=opp.number_of_containers,
        target_shipment_date=opp.target_shipment_date.isoformat() if opp.target_shipment_date else None,
        shipping_line=opp.shipping_line,
        packaging_requirements=opp.packaging_requirements,
        quality_specifications=opp.quality_specifications,
        expected_close_date=opp.expected_close_date.isoformat() if opp.expected_close_date else None,
        follow_up_date=opp.follow_up_date.isoformat() if opp.follow_up_date else None,
        probability=opp.probability,
        sample_sent=opp.sample_sent,
        sample_approved=opp.sample_approved,
        sample_feedback=opp.sample_feedback,
        currency=opp.currency or "USD",
        loss_reason=opp.loss_reason,
        notes=opp.notes,
        assigned_to=str(opp.assigned_to) if opp.assigned_to else None,
        tags=opp.tags,
        is_archived=opp.is_archived,
        sample_sent_date=opp.sample_sent_date.isoformat() if opp.sample_sent_date else None,
        closed_at=opp.closed_at.isoformat() if opp.closed_at else None,
        created_at=opp.created_at.isoformat(), updated_at=opp.updated_at.isoformat(),
    )


@router.get("/stages", response_model=list)
async def get_stages(
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    stages = await _ensure_default_stages(db, tenant_id)
    return [
        PipelineStageResponse(
            id=str(s.id), name=s.name, slug=s.slug, order=s.order, color=s.color,
        )
        for s in sorted(stages, key=lambda x: x.order)
    ]


@router.get("", response_model=list)
async def list_opportunities(
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
    company_id: Optional[uuid.UUID] = None,
    contact_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
):
    """List all opportunities, optionally filtered by company or contact."""
    stages = await _ensure_default_stages(db, tenant_id)

    query = select(PipelineOpportunity).where(
        PipelineOpportunity.tenant_id == tenant_id,
        PipelineOpportunity.is_archived.is_(False),
    )
    if company_id:
        query = query.where(PipelineOpportunity.company_id == company_id)
    if contact_id:
        query = query.where(PipelineOpportunity.contact_id == contact_id)
    if active_only:
        closed_ids = [s.id for s in stages if s.slug in ("closed_won", "closed_lost")]
        if closed_ids:
            query = query.where(PipelineOpportunity.stage_id.notin_(closed_ids))

    result = await db.execute(query.order_by(desc(PipelineOpportunity.updated_at)))
    opps = result.scalars().all()
    return [await _opp_response(db, o) for o in opps]


@router.post("", response_model=OpportunityResponse, status_code=201)
async def create_opportunity(
    body: OpportunityCreate, user: CurrentUser,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    stages = await _ensure_default_stages(db, tenant_id)

    stage_id = body.stage_id
    if not stage_id:
        stage_id = stages[0].id  # default to "New Lead"

    # Validate company exists
    company = (await db.execute(
        select(Company).where(Company.id == body.company_id, Company.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    display_id = await _generate_display_id(db, tenant_id)

    opp = PipelineOpportunity(
        tenant_id=tenant_id, company_id=body.company_id,
        contact_id=body.contact_id, stage_id=stage_id,
        display_id=display_id,
        title=body.title,
        source=OpportunitySource(body.source) if body.source in [s.value for s in OpportunitySource] else OpportunitySource.manual,
        value=body.value, commodity=body.commodity,
        quantity_mt=body.quantity_mt,
        target_price=body.target_price, our_price=body.our_price,
        competitor_price=body.competitor_price,
        incoterms=body.incoterms, payment_terms=body.payment_terms,
        container_type=body.container_type,
        number_of_containers=body.number_of_containers,
        packaging_requirements=body.packaging_requirements,
        quality_specifications=body.quality_specifications,
        notes=body.notes,
    )
    db.add(opp)

    # Log activity
    db.add(ActivityLog(
        tenant_id=tenant_id, actor_type=ActorType.user, actor_id=user.id,
        action="opportunity_created", entity_type="pipeline",
        entity_id=opp.id, detail={"company": company.name, "stage": "new_lead"},
    ))

    await db.commit()
    await db.refresh(opp)
    logger.info("Opportunity created: id=%s company=%s", opp.id, company.name)
    return await _opp_response(db, opp)


@router.put("/{opp_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opp_id: uuid.UUID, body: OpportunityUpdate,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    opp = (await db.execute(
        select(PipelineOpportunity).where(
            PipelineOpportunity.id == opp_id, PipelineOpportunity.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(opp, field, value)
    await db.commit()
    await db.refresh(opp)
    return await _opp_response(db, opp)


@router.put("/{opp_id}/move", response_model=OpportunityResponse)
async def move_opportunity(
    opp_id: uuid.UUID, body: OpportunityMoveRequest,
    user: CurrentUser, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Move opportunity to a different pipeline stage."""
    opp = (await db.execute(
        select(PipelineOpportunity).where(
            PipelineOpportunity.id == opp_id, PipelineOpportunity.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Validate target stage
    new_stage = (await db.execute(
        select(PipelineStage).where(
            PipelineStage.id == body.stage_id, PipelineStage.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not new_stage:
        raise HTTPException(status_code=404, detail="Target stage not found")

    old_stage = (await db.execute(
        select(PipelineStage).where(PipelineStage.id == opp.stage_id)
    )).scalar_one_or_none()

    opp.stage_id = body.stage_id
    if new_stage.slug in ("closed_won", "closed_lost"):
        opp.closed_at = datetime.now(timezone.utc)

    # Log stage change
    db.add(ActivityLog(
        tenant_id=tenant_id, actor_type=ActorType.user, actor_id=user.id,
        action="opportunity_stage_changed", entity_type="pipeline", entity_id=opp.id,
        detail={
            "from_stage": old_stage.name if old_stage else "unknown",
            "to_stage": new_stage.name,
        },
    ))

    await db.commit()
    await db.refresh(opp)
    logger.info("Opportunity moved: id=%s to=%s", opp_id, new_stage.name)
    return await _opp_response(db, opp)


@router.delete("/{opp_id}", status_code=204)
async def archive_opportunity(
    opp_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    opp = (await db.execute(
        select(PipelineOpportunity).where(
            PipelineOpportunity.id == opp_id, PipelineOpportunity.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.is_archived = True
    await db.commit()
    logger.info("Opportunity archived: id=%s", opp_id)


@router.get("/stats", response_model=PipelineStats)
async def get_pipeline_stats(
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    stages = await _ensure_default_stages(db, tenant_id)

    total = (await db.execute(
        select(func.count()).where(
            PipelineOpportunity.tenant_id == tenant_id,
            PipelineOpportunity.is_archived.is_(False),
        )
    )).scalar() or 0

    total_value = (await db.execute(
        select(func.sum(PipelineOpportunity.value)).where(
            PipelineOpportunity.tenant_id == tenant_id,
            PipelineOpportunity.is_archived.is_(False),
        )
    )).scalar() or 0

    by_stage = []
    for stage in sorted(stages, key=lambda s: s.order):
        count = (await db.execute(
            select(func.count()).where(
                PipelineOpportunity.tenant_id == tenant_id,
                PipelineOpportunity.stage_id == stage.id,
                PipelineOpportunity.is_archived.is_(False),
            )
        )).scalar() or 0
        by_stage.append({"stage": stage.name, "color": stage.color, "count": count})

    return PipelineStats(
        total_opportunities=total,
        total_value=float(total_value),
        by_stage=by_stage,
    )


@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opp_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get a single opportunity by ID."""
    opp = (await db.execute(
        select(PipelineOpportunity).where(
            PipelineOpportunity.id == opp_id,
            PipelineOpportunity.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return await _opp_response(db, opp)
