"""Product-Port Interests API — CRUD + bulk actions + AI inference."""
from typing import Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.product_port_interest import ProductPortInterest
from app.models.catalog import Product, ProductVariety, ProductGrade, Port
from app.models.enums import InterestRole, InterestSource, ConfidenceLevel, InterestStatus
from app.schemas.interests import (
    InterestCreate, InterestUpdate, InterestResponse, BulkActionRequest,
)

logger = get_logger("api.interests")
router = APIRouter(prefix="/interests", tags=["interests"])


async def _interest_response(db: AsyncSession, i: ProductPortInterest) -> InterestResponse:
    """Build response with resolved names."""
    product = (await db.execute(select(Product).where(Product.id == i.product_id))).scalar_one_or_none()
    variety = (await db.execute(select(ProductVariety).where(ProductVariety.id == i.variety_id))).scalar_one_or_none() if i.variety_id else None
    grade = (await db.execute(select(ProductGrade).where(ProductGrade.id == i.grade_id))).scalar_one_or_none() if i.grade_id else None
    dest_port = (await db.execute(select(Port).where(Port.id == i.destination_port_id))).scalar_one_or_none() if i.destination_port_id else None
    orig_port = (await db.execute(select(Port).where(Port.id == i.origin_port_id))).scalar_one_or_none() if i.origin_port_id else None

    return InterestResponse(
        id=str(i.id), tenant_id=str(i.tenant_id),
        company_id=str(i.company_id) if i.company_id else None,
        contact_id=str(i.contact_id) if i.contact_id else None,
        product_id=str(i.product_id),
        product_name=product.name if product else None,
        variety_id=str(i.variety_id) if i.variety_id else None,
        variety_name=variety.name if variety else None,
        grade_id=str(i.grade_id) if i.grade_id else None,
        grade_name=grade.name if grade else None,
        destination_port_id=str(i.destination_port_id) if i.destination_port_id else None,
        destination_port_name=dest_port.name if dest_port else None,
        origin_port_id=str(i.origin_port_id) if i.origin_port_id else None,
        origin_port_name=orig_port.name if orig_port else None,
        role=i.role.value, source=i.source.value,
        confidence=float(i.confidence) if i.confidence else None,
        confidence_level=i.confidence_level.value if i.confidence_level else None,
        evidence=i.evidence, status=i.status.value,
        confirmed_by=str(i.confirmed_by) if i.confirmed_by else None,
        confirmed_at=i.confirmed_at.isoformat() if i.confirmed_at else None,
        notes=i.notes,
        created_at=i.created_at.isoformat(), updated_at=i.updated_at.isoformat(),
    )


@router.get("", response_model=list)
async def list_interests(
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
    company_id: Optional[uuid.UUID] = None,
    contact_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    product_id: Optional[uuid.UUID] = None,
):
    query = select(ProductPortInterest).where(ProductPortInterest.tenant_id == tenant_id)
    if company_id:
        query = query.where(ProductPortInterest.company_id == company_id)
    if contact_id:
        query = query.where(ProductPortInterest.contact_id == contact_id)
    if status:
        query = query.where(ProductPortInterest.status == status)
    if product_id:
        query = query.where(ProductPortInterest.product_id == product_id)

    result = await db.execute(query.order_by(desc(ProductPortInterest.confidence)))
    return [await _interest_response(db, i) for i in result.scalars().all()]


@router.get("/{interest_id}", response_model=InterestResponse)
async def get_interest(
    interest_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    i = (await db.execute(
        select(ProductPortInterest).where(
            ProductPortInterest.id == interest_id, ProductPortInterest.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not i:
        raise HTTPException(status_code=404, detail="Interest not found")
    return await _interest_response(db, i)


@router.post("", response_model=InterestResponse, status_code=201)
async def create_interest(
    body: InterestCreate, user: CurrentUser,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    """Create a manual interest (confidence=1.0, status=confirmed)."""
    conf_level = ConfidenceLevel.high

    i = ProductPortInterest(
        tenant_id=tenant_id,
        company_id=body.company_id, contact_id=body.contact_id,
        product_id=body.product_id,
        variety_id=body.variety_id, grade_id=body.grade_id,
        destination_port_id=body.destination_port_id,
        origin_port_id=body.origin_port_id,
        role=InterestRole(body.role) if body.role in [r.value for r in InterestRole] else InterestRole.buyer,
        source=InterestSource.manual,
        confidence=1.0, confidence_level=conf_level,
        status=InterestStatus.confirmed,
        confirmed_by=user.id,
        confirmed_at=datetime.now(timezone.utc),
        notes=body.notes,
    )
    db.add(i)
    await db.commit()
    await db.refresh(i)
    logger.info("Interest created: id=%s product=%s company=%s", i.id, body.product_id, body.company_id)
    return await _interest_response(db, i)


@router.put("/{interest_id}", response_model=InterestResponse)
async def update_interest(
    interest_id: uuid.UUID, body: InterestUpdate,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    i = (await db.execute(
        select(ProductPortInterest).where(
            ProductPortInterest.id == interest_id, ProductPortInterest.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not i:
        raise HTTPException(status_code=404, detail="Interest not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "role" and value:
            value = InterestRole(value) if value in [r.value for r in InterestRole] else i.role
        setattr(i, field, value)

    await db.commit()
    await db.refresh(i)
    return await _interest_response(db, i)


@router.delete("/{interest_id}", status_code=204)
async def delete_interest(
    interest_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    i = (await db.execute(
        select(ProductPortInterest).where(
            ProductPortInterest.id == interest_id, ProductPortInterest.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not i:
        raise HTTPException(status_code=404, detail="Interest not found")
    await db.delete(i)
    await db.commit()
    logger.info("Interest deleted: id=%s", interest_id)


@router.post("/bulk-accept", status_code=200)
async def bulk_accept(
    body: BulkActionRequest, user: CurrentUser,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    """Accept multiple suggested interests."""
    now = datetime.now(timezone.utc)
    accepted = 0
    for iid in body.interest_ids:
        i = (await db.execute(
            select(ProductPortInterest).where(
                ProductPortInterest.id == iid, ProductPortInterest.tenant_id == tenant_id,
                ProductPortInterest.status == InterestStatus.suggested,
            )
        )).scalar_one_or_none()
        if i:
            i.status = InterestStatus.confirmed
            i.confirmed_by = user.id
            i.confirmed_at = now
            accepted += 1

    await db.commit()
    logger.info("Bulk accept: %d interests confirmed", accepted)
    return {"accepted": accepted}


@router.post("/bulk-reject", status_code=200)
async def bulk_reject(
    body: BulkActionRequest,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    """Reject multiple suggested interests."""
    rejected = 0
    for iid in body.interest_ids:
        i = (await db.execute(
            select(ProductPortInterest).where(
                ProductPortInterest.id == iid, ProductPortInterest.tenant_id == tenant_id,
                ProductPortInterest.status == InterestStatus.suggested,
            )
        )).scalar_one_or_none()
        if i:
            i.status = InterestStatus.rejected
            rejected += 1

    await db.commit()
    logger.info("Bulk reject: %d interests rejected", rejected)
    return {"rejected": rejected}


@router.post("/infer/{company_id}", status_code=200)
async def infer_company_interests(
    company_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI inference to discover product-port interests for a company."""
    from app.agents.interest_inference_agent import infer_interests

    results = await infer_interests(db, tenant_id, company_id)
    await db.commit()

    return {"suggestions_created": len(results), "details": results}
