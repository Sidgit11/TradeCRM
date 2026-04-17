from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId
from app.models.company import Company
from app.models.enums import CompanySource
from app.schemas.companies import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    PaginatedCompanies,
)
from app.utils.response import model_to_response

logger = get_logger("api.companies")
router = APIRouter(prefix="/companies", tags=["companies"])


def _company_response(c: Company) -> CompanyResponse:
    return model_to_response(c, CompanyResponse, exclude={"is_deleted", "enrichment_data", "confidence_score", "logo_url"},
        commodities=c.commodities or [],
    )


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    company = Company(
        tenant_id=tenant_id,
        name=body.name, description=body.description,
        country=body.country, city=body.city, state=body.state,
        postal_code=body.postal_code, address=body.address,
        phone=body.phone, email=body.email,
        website=body.website, industry=body.industry,
        company_type=body.company_type, company_size=body.company_size,
        year_established=body.year_established,
        number_of_employees=body.number_of_employees,
        annual_revenue_usd=body.annual_revenue_usd,
        registration_number=body.registration_number,
        commodities=body.commodities,
        preferred_origins=body.preferred_origins,
        preferred_incoterms=body.preferred_incoterms,
        preferred_payment_terms=body.preferred_payment_terms,
        certifications_required=body.certifications_required,
        destination_ports=body.destination_ports,
        import_volume_annual=body.import_volume_annual,
        shipment_frequency=body.shipment_frequency,
        bank_name=body.bank_name, bank_country=body.bank_country,
        bank_swift_code=body.bank_swift_code,
        linkedin_url=body.linkedin_url, tax_id=body.tax_id,
        rating=body.rating, tags=body.tags,
        known_suppliers=body.known_suppliers,
        trade_references=body.trade_references,
        social_media=body.social_media,
        source=CompanySource(body.source) if body.source in [s.value for s in CompanySource] else CompanySource.manual,
        notes=body.notes,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    logger.info("Company created: id=%s name=%s tenant=%s", company.id, company.name, tenant_id)
    return _company_response(company)


@router.get("", response_model=PaginatedCompanies)
async def list_companies(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    country: Optional[str] = None,
    commodity: Optional[str] = None,
    enrichment_status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    query = select(Company).where(
        Company.tenant_id == tenant_id,
        Company.is_deleted.is_(False),
    )

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Company.name.ilike(search_term),
                Company.country.ilike(search_term),
            )
        )

    if country:
        query = query.where(Company.country.ilike(f"%{country}%"))

    if commodity:
        query = query.where(Company.commodities.cast(String).ilike(f"%{commodity}%"))

    if enrichment_status:
        query = query.where(Company.enrichment_status == enrichment_status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    sort_col = getattr(Company, sort_by, Company.created_at)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    companies = result.scalars().all()

    return PaginatedCompanies(
        items=[_company_response(c) for c in companies],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
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
    return _company_response(company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    body: CompanyUpdate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
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

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    logger.info("Company updated: id=%s tenant=%s", company_id, tenant_id)
    return _company_response(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant_id,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    company.is_deleted = True
    await db.commit()
    logger.info("Company soft-deleted: id=%s tenant=%s", company_id, tenant_id)


@router.post("/{company_id}/notes", status_code=status.HTTP_200_OK)
async def add_company_note(
    company_id: uuid.UUID,
    body: dict,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
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

    note = body.get("note", "")
    existing = company.notes or ""
    company.notes = f"{existing}\n\n{note}".strip() if existing else note
    await db.commit()
    return {"status": "ok"}
