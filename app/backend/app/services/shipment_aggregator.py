"""Shipment Aggregator — computes summary from raw shipment rows."""
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.shipment import Shipment
from app.models.shipment_summary import CompanyShipmentSummary
from app.models.catalog import Product
from app.services.catalog_matcher import match_commodity_to_catalog

logger = get_logger("services.shipment_aggregator")


async def compute_summary(
    db: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID,
) -> Optional[CompanyShipmentSummary]:
    """Compute or refresh the shipment summary for a company."""
    # Fetch all shipments
    result = await db.execute(
        select(Shipment).where(
            Shipment.tenant_id == tenant_id,
            Shipment.company_id == company_id,
        ).order_by(desc(Shipment.shipment_date))
    )
    shipments = list(result.scalars().all())

    if not shipments:
        return None

    today = date.today()
    twelve_months_ago = today - timedelta(days=365)

    # Fetch catalog products for matching
    products = list((await db.execute(
        select(Product).where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
    )).scalars().all())

    # Match shipments to catalog
    catalog_matched = 0
    catalog_matched_vol = 0.0
    for s in shipments:
        if not s.matched_product_id:
            pid, conf = match_commodity_to_catalog(s.commodity_text, products)
            if pid:
                s.matched_product_id = uuid.UUID(pid)
                s.match_confidence = conf

        if s.matched_product_id:
            catalog_matched += 1
            catalog_matched_vol += float(s.volume_mt or 0)

    # All-time totals
    total_shipments = len(shipments)
    total_vol = sum(float(s.volume_mt or 0) for s in shipments)
    total_val = sum(float(s.value_usd or 0) for s in shipments)

    # 12-month
    recent = [s for s in shipments if s.shipment_date >= twelve_months_ago]
    shipments_12mo = len(recent)
    vol_12mo = sum(float(s.volume_mt or 0) for s in recent)
    val_12mo = sum(float(s.value_usd or 0) for s in recent)

    # Role inference
    import_count = sum(1 for s in shipments if s.direction.value == "import")
    export_count = total_shipments - import_count
    if import_count > 0 and export_count > 0:
        role = "re_exporter" if abs(import_count - export_count) < total_shipments * 0.3 else ("importer" if import_count > export_count else "exporter")
    elif import_count > 0:
        role = "importer"
    elif export_count > 0:
        role = "exporter"
    else:
        role = "unknown"

    # Cadence (from recent shipments)
    if shipments_12mo >= 10:
        cadence = "monthly"
    elif shipments_12mo >= 4:
        cadence = "quarterly"
    elif shipments_12mo >= 2:
        cadence = "biannual"
    elif shipments_12mo >= 1:
        cadence = "annual"
    else:
        cadence = "none"

    # Average price
    prices = [float(s.unit_price_usd_per_mt) for s in shipments if s.unit_price_usd_per_mt]
    avg_price = sum(prices) / len(prices) if prices else None
    price_min = min(prices) if prices else None
    price_max = max(prices) if prices else None

    # Top partners
    partner_stats = defaultdict(lambda: {"shipments": 0, "volume_mt": 0})
    for s in shipments:
        if s.trade_partner_name:
            ps = partner_stats[s.trade_partner_name]
            ps["shipments"] += 1
            ps["volume_mt"] += float(s.volume_mt or 0)
            ps["country"] = s.trade_partner_country or ""
            ps["company_id"] = str(s.trade_partner_company_id) if s.trade_partner_company_id else None

    top_partners = sorted(
        [{"name": k, **v} for k, v in partner_stats.items()],
        key=lambda x: x["volume_mt"], reverse=True
    )[:5]

    # Top lanes
    lane_stats = defaultdict(lambda: {"shipments": 0, "volume_mt": 0})
    for s in shipments:
        origin = s.origin_port_text or "Unknown"
        dest = s.destination_port_text or "Unknown"
        lane_key = f"{origin} → {dest}"
        ls = lane_stats[lane_key]
        ls["shipments"] += 1
        ls["volume_mt"] += float(s.volume_mt or 0)
        ls["origin_port"] = origin
        ls["destination_port"] = dest

    top_lanes = sorted(
        [v for v in lane_stats.values()],
        key=lambda x: x["volume_mt"], reverse=True
    )[:5]

    # Top commodities
    commodity_stats = defaultdict(lambda: {"shipments": 0, "volume_mt": 0, "avg_price": 0, "prices": [], "last_date": None, "hs": None, "product_id": None})
    for s in shipments:
        cs = commodity_stats[s.commodity_text]
        cs["shipments"] += 1
        cs["volume_mt"] += float(s.volume_mt or 0)
        if s.unit_price_usd_per_mt:
            cs["prices"].append(float(s.unit_price_usd_per_mt))
        if cs["last_date"] is None or s.shipment_date > cs["last_date"]:
            cs["last_date"] = s.shipment_date
        cs["hs"] = s.hs_code
        if s.matched_product_id:
            cs["product_id"] = str(s.matched_product_id)

    top_commodities = []
    for name, cs in sorted(commodity_stats.items(), key=lambda x: x[1]["volume_mt"], reverse=True)[:10]:
        avg_p = sum(cs["prices"]) / len(cs["prices"]) if cs["prices"] else None
        top_commodities.append({
            "name": name, "hs": cs["hs"], "matched_product_id": cs["product_id"],
            "shipments": cs["shipments"], "volume_mt": cs["volume_mt"],
            "avg_price": avg_p, "last_date": cs["last_date"].isoformat() if cs["last_date"] else None,
        })

    # Monthly series (24 months)
    monthly = defaultdict(lambda: {"volume_mt": 0, "shipments": 0})
    for s in shipments:
        month_key = s.shipment_date.strftime("%Y-%m")
        monthly[month_key]["volume_mt"] += float(s.volume_mt or 0)
        monthly[month_key]["shipments"] += 1

    # Fill gaps for last 24 months
    monthly_series = []
    for i in range(24):
        d = today - timedelta(days=30 * i)
        key = d.strftime("%Y-%m")
        monthly_series.append({"month": key, **monthly.get(key, {"volume_mt": 0, "shipments": 0})})
    monthly_series.reverse()

    # Upsert summary
    existing = (await db.execute(
        select(CompanyShipmentSummary).where(
            CompanyShipmentSummary.tenant_id == tenant_id,
            CompanyShipmentSummary.company_id == company_id,
        )
    )).scalar_one_or_none()

    if existing:
        summary = existing
    else:
        summary = CompanyShipmentSummary(tenant_id=tenant_id, company_id=company_id)
        db.add(summary)

    summary.last_refreshed_at = datetime.now(timezone.utc)
    summary.data_through_date = shipments[0].shipment_date if shipments else today
    summary.source_providers = ["tradecrm_internal"]
    summary.total_shipments = total_shipments
    summary.total_volume_mt = total_vol
    summary.total_value_usd = total_val
    summary.shipments_12mo = shipments_12mo
    summary.volume_12mo_mt = vol_12mo
    summary.value_12mo_usd = val_12mo
    summary.role = role
    summary.cadence = cadence
    summary.avg_unit_price_usd_per_mt = avg_price
    summary.price_min = price_min
    summary.price_max = price_max
    summary.top_partners = top_partners
    summary.top_lanes = top_lanes
    summary.top_commodities = top_commodities
    summary.monthly_series = monthly_series
    summary.catalog_match_count = catalog_matched
    summary.catalog_match_volume_mt = catalog_matched_vol

    await db.flush()
    logger.info("Shipment summary computed: company=%s shipments=%d vol=%.0f MT",
        str(company_id)[:8], total_shipments, total_vol)

    return summary
