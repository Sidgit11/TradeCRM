"""Shipment Intelligence API — company trade history endpoints."""
from typing import Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId
from app.models.shipment import Shipment
from app.models.shipment_summary import CompanyShipmentSummary
from app.models.company import Company
from app.schemas.shipments import ShipmentResponse, ShipmentSummaryResponse
from app.services.shipment_aggregator import compute_summary

logger = get_logger("api.shipments")
router = APIRouter(prefix="/companies", tags=["shipments"])


@router.get("/{company_id}/shipments/summary", response_model=ShipmentSummaryResponse)
async def get_shipment_summary(
    company_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get precomputed shipment summary for a company."""
    # Validate company
    company = (await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get or compute summary
    summary = (await db.execute(
        select(CompanyShipmentSummary).where(
            CompanyShipmentSummary.company_id == company_id,
            CompanyShipmentSummary.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not summary:
        # Compute on first access
        summary = await compute_summary(db, tenant_id, company_id)
        await db.commit()

    if not summary:
        return ShipmentSummaryResponse(
            company_id=str(company_id),
            totals={"shipments_12mo": 0, "volume_12mo_mt": 0, "value_12mo_usd": 0},
        )

    return ShipmentSummaryResponse(
        company_id=str(company_id),
        last_refreshed_at=summary.last_refreshed_at.isoformat() if summary.last_refreshed_at else None,
        data_through_date=summary.data_through_date.isoformat() if summary.data_through_date else None,
        source_providers=summary.source_providers or [],
        role=summary.role.value if summary.role else None,
        cadence=summary.cadence.value if summary.cadence else None,
        totals={
            "shipments_12mo": summary.shipments_12mo,
            "volume_12mo_mt": float(summary.volume_12mo_mt or 0),
            "value_12mo_usd": float(summary.value_12mo_usd or 0),
            "total_shipments": summary.total_shipments,
            "total_volume_mt": float(summary.total_volume_mt or 0),
            "avg_unit_price_usd_per_mt": float(summary.avg_unit_price_usd_per_mt) if summary.avg_unit_price_usd_per_mt else None,
            "price_range": [float(summary.price_min or 0), float(summary.price_max or 0)] if summary.price_min else None,
        },
        monthly_series=summary.monthly_series or [],
        top_partners=summary.top_partners or [],
        top_lanes=summary.top_lanes or [],
        top_commodities=summary.top_commodities or [],
        catalog_match_ratio=(summary.catalog_match_count / summary.total_shipments) if summary.total_shipments > 0 else 0,
    )


@router.get("/{company_id}/shipments", response_model=list)
async def list_shipments(
    company_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    direction: Optional[str] = None,
    commodity: Optional[str] = None,
    catalog_only: bool = False,
    limit: int = Query(25, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """List raw shipment records for a company."""
    query = select(Shipment).where(
        Shipment.company_id == company_id,
        Shipment.tenant_id == tenant_id,
    )

    if direction:
        query = query.where(Shipment.direction == direction)
    if commodity:
        query = query.where(Shipment.commodity_text.ilike(f"%{commodity}%"))
    if catalog_only:
        query = query.where(Shipment.matched_product_id.isnot(None))

    total_q = select(Shipment).where(Shipment.company_id == company_id, Shipment.tenant_id == tenant_id)
    result = await db.execute(query.order_by(desc(Shipment.shipment_date)).offset(skip).limit(limit))
    shipments = result.scalars().all()

    return [
        ShipmentResponse(
            id=str(s.id), company_id=str(s.company_id),
            shipment_date=s.shipment_date.isoformat(),
            direction=s.direction.value,
            commodity_text=s.commodity_text, hs_code=s.hs_code,
            origin_country=s.origin_country, destination_country=s.destination_country,
            origin_port_text=s.origin_port_text, destination_port_text=s.destination_port_text,
            volume_mt=float(s.volume_mt) if s.volume_mt else None,
            unit_price_usd_per_mt=float(s.unit_price_usd_per_mt) if s.unit_price_usd_per_mt else None,
            value_usd=float(s.value_usd) if s.value_usd else None,
            trade_partner_name=s.trade_partner_name,
            trade_partner_country=s.trade_partner_country,
            matched_product_id=str(s.matched_product_id) if s.matched_product_id else None,
            match_confidence=float(s.match_confidence) if s.match_confidence else None,
            created_at=s.created_at.isoformat(),
        )
        for s in shipments
    ]


@router.get("/{company_id}/shipments/partners", response_model=list)
async def list_shipment_partners(
    company_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get trade partners aggregation from shipments."""
    summary = (await db.execute(
        select(CompanyShipmentSummary).where(
            CompanyShipmentSummary.company_id == company_id,
            CompanyShipmentSummary.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not summary or not summary.top_partners:
        return []
    return summary.top_partners


@router.get("/{company_id}/shipments/commodities", response_model=list)
async def list_shipment_commodities(
    company_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get commodity breakdown from shipments."""
    summary = (await db.execute(
        select(CompanyShipmentSummary).where(
            CompanyShipmentSummary.company_id == company_id,
            CompanyShipmentSummary.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not summary or not summary.top_commodities:
        return []
    return summary.top_commodities


@router.post("/{company_id}/shipments/refresh", status_code=200)
async def refresh_shipments(
    company_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Force-refresh shipment data for a company."""
    company = (await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    summary = await compute_summary(db, tenant_id, company_id)
    await db.commit()

    return {
        "status": "refreshed",
        "company_id": str(company_id),
        "shipments": summary.total_shipments if summary else 0,
        "volume_mt": float(summary.total_volume_mt or 0) if summary else 0,
    }
