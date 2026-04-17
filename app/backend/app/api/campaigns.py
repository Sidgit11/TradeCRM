"""Campaign API — builder, execution, approval flow, analytics."""
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.campaign import Campaign, CampaignStep
from app.models.message import Message
from app.models.sequence import Sequence
from app.models.enums import (
    CampaignStatus, CampaignType, ChannelType, StepCondition,
    MessageStatus, SequenceStatus,
)
from app.schemas.campaigns import (
    CampaignCreate, CampaignResponse, CampaignStepCreate,
    CampaignStepResponse, CampaignUpdate, CampaignStepReorder,
    CampaignAnalytics,
)

logger = get_logger("api.campaigns")
router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _step_response(s: CampaignStep) -> CampaignStepResponse:
    return CampaignStepResponse(
        id=str(s.id), step_number=s.step_number, channel=s.channel.value,
        delay_days=s.delay_days, condition=s.condition.value,
        template_content=s.template_content,
        whatsapp_template_name=s.whatsapp_template_name,
        subject_template=s.subject_template,
    )


def _campaign_response(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        id=str(c.id), tenant_id=str(c.tenant_id), name=c.name,
        type=c.type.value, status=c.status.value,
        contact_list_id=str(c.contact_list_id) if c.contact_list_id else None,
        created_by=str(c.created_by),
        scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else None,
        started_at=c.started_at.isoformat() if c.started_at else None,
        completed_at=c.completed_at.isoformat() if c.completed_at else None,
        settings=c.settings or {},
        steps=[_step_response(s) for s in (c.steps or [])],
        created_at=c.created_at.isoformat(), updated_at=c.updated_at.isoformat(),
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(
        tenant_id=tenant_id, name=body.name,
        type=CampaignType(body.type), status=CampaignStatus.draft,
        contact_list_id=body.contact_list_id, created_by=user.id,
        settings=body.settings,
    )
    db.add(campaign)
    await db.flush()

    for i, step in enumerate(body.steps):
        db.add(CampaignStep(
            campaign_id=campaign.id, step_number=i + 1,
            channel=ChannelType(step.channel), delay_days=step.delay_days,
            condition=StepCondition(step.condition),
            template_content=step.template_content,
            whatsapp_template_name=step.whatsapp_template_name,
            subject_template=step.subject_template,
        ))

    await db.commit()
    await db.refresh(campaign)
    logger.info("Campaign created: id=%s name=%s tenant=%s", campaign.id, campaign.name, tenant_id)
    return _campaign_response(campaign)


@router.get("", response_model=list)
async def list_campaigns(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(25, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    query = select(Campaign).where(Campaign.tenant_id == tenant_id)
    if status_filter:
        query = query.where(Campaign.status == status_filter)
    query = query.order_by(desc(Campaign.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return [_campaign_response(c) for c in result.scalars().all()]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_response(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID, body: CampaignUpdate,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.tenant_id == tenant_id,
            Campaign.status == CampaignStatus.draft,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found or not in draft")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    await db.commit()
    await db.refresh(campaign)
    return _campaign_response(campaign)


@router.post("/{campaign_id}/steps", response_model=CampaignStepResponse, status_code=201)
async def add_campaign_step(
    campaign_id: uuid.UUID, body: CampaignStepCreate,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    campaign = (await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    max_step = (await db.execute(
        select(func.max(CampaignStep.step_number)).where(CampaignStep.campaign_id == campaign_id)
    )).scalar() or 0

    step = CampaignStep(
        campaign_id=campaign_id, step_number=max_step + 1,
        channel=ChannelType(body.channel), delay_days=body.delay_days,
        condition=StepCondition(body.condition),
        template_content=body.template_content,
        whatsapp_template_name=body.whatsapp_template_name,
        subject_template=body.subject_template,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    logger.info("Step added: campaign=%s step=%d", campaign_id, step.step_number)
    return _step_response(step)


@router.delete("/{campaign_id}/steps/{step_id}", status_code=204)
async def delete_campaign_step(
    campaign_id: uuid.UUID, step_id: uuid.UUID,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    campaign = (await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    step = (await db.execute(
        select(CampaignStep).where(CampaignStep.id == step_id, CampaignStep.campaign_id == campaign_id)
    )).scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    await db.delete(step)
    await db.commit()


class ActivateRequest(BaseModel):
    contact_ids: Optional[list] = None


@router.post("/{campaign_id}/activate", status_code=200)
async def activate_campaign(
    campaign_id: uuid.UUID, user: CurrentUser,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
    body: Optional[ActivateRequest] = None,
):
    from app.services.campaign_executor import execute_campaign

    campaign = (await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.tenant_id == tenant_id,
            Campaign.status.in_([CampaignStatus.draft, CampaignStatus.paused]),
        )
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=400, detail="Campaign not found or not in draft/paused")

    campaign.status = CampaignStatus.active
    campaign.started_at = datetime.now(timezone.utc)
    await db.commit()

    # Execute immediately — send step 1 messages
    cids = None
    if body and body.contact_ids:
        cids = [uuid.UUID(c) if isinstance(c, str) else c for c in body.contact_ids]
    result = await execute_campaign(db, campaign_id, tenant_id, contact_ids=cids)

    if result.get("error"):
        logger.warning("Campaign activation partial: id=%s error=%s", campaign_id, result["error"])
    else:
        logger.info("Campaign activated+executed: id=%s sent=%d failed=%d",
            campaign_id, result.get("sent", 0), result.get("failed", 0))

    # Mark completed if single step
    if len(campaign.steps) <= 1:
        campaign.status = CampaignStatus.completed
        campaign.completed_at = datetime.now(timezone.utc)
        await db.commit()

    return {
        "status": "active",
        "campaign_id": str(campaign_id),
        "execution": result,
    }


@router.post("/{campaign_id}/pause", status_code=200)
async def pause_campaign(
    campaign_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    campaign = (await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.tenant_id == tenant_id,
            Campaign.status == CampaignStatus.active,
        )
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=400, detail="Campaign not found or not active")
    campaign.status = CampaignStatus.paused
    await db.commit()
    logger.info("Campaign paused: id=%s", campaign_id)
    return {"status": "paused"}


@router.post("/{campaign_id}/cancel", status_code=200)
async def cancel_campaign(
    campaign_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    campaign = (await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status in (CampaignStatus.completed, CampaignStatus.cancelled):
        raise HTTPException(status_code=400, detail="Campaign already finished")
    campaign.status = CampaignStatus.cancelled
    await db.commit()
    logger.info("Campaign cancelled: id=%s", campaign_id)
    return {"status": "cancelled"}


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalytics)
async def get_campaign_analytics(
    campaign_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    campaign = (await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    base = select(Message).where(Message.campaign_id == campaign_id, Message.tenant_id == tenant_id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    delivered = (await db.execute(select(func.count()).select_from(
        base.where(Message.delivered_at.isnot(None)).subquery()
    ))).scalar() or 0
    opened = (await db.execute(select(func.count()).select_from(
        base.where(Message.opened_at.isnot(None)).subquery()
    ))).scalar() or 0
    replied = (await db.execute(select(func.count()).select_from(
        base.where(Message.replied_at.isnot(None)).subquery()
    ))).scalar() or 0
    failed = (await db.execute(select(func.count()).select_from(
        base.where(Message.status == MessageStatus.failed).subquery()
    ))).scalar() or 0
    bounced = (await db.execute(select(func.count()).select_from(
        base.where(Message.status == MessageStatus.bounced).subquery()
    ))).scalar() or 0

    return CampaignAnalytics(
        total_sent=total, delivered=delivered,
        delivery_rate=round(delivered / total * 100, 1) if total else 0,
        opened=opened, open_rate=round(opened / delivered * 100, 1) if delivered else 0,
        replied=replied, reply_rate=round(replied / delivered * 100, 1) if delivered else 0,
        failed=failed, bounced=bounced,
    )
