"""Interest Inference Agent — AI-powered product-port interest discovery.

Reads company enrichment data, commodities, shipment history, email/WA threads
and infers which products from the tenant's catalog the company is interested in,
at which ports, with confidence scores and evidence.
"""
import uuid
from typing import Dict, List, Optional

import httpx
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging_config import get_logger
from app.utils.gemini import safe_parse_json, GEMINI_URL, extract_gemini_text
from app.models.company import Company
from app.models.contact import Contact
from app.models.catalog import Product, Port
from app.models.shipment import Shipment
from app.models.message import Message
from app.models.product_port_interest import ProductPortInterest
from app.models.enums import (
    InterestRole, InterestSource, ConfidenceLevel, InterestStatus,
    ShipmentDirection, MessageDirection,
)
from app.services.catalog_matcher import match_commodity_to_catalog

logger = get_logger("agents.interest_inference")


def _confidence_level(confidence: float) -> ConfidenceLevel:
    if confidence >= 0.8:
        return ConfidenceLevel.high
    if confidence >= 0.5:
        return ConfidenceLevel.medium
    return ConfidenceLevel.low


async def infer_interests(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
) -> List[Dict]:
    """Run inference pipeline for a company. Returns list of created/updated interest dicts."""
    company = (await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not company:
        return []

    # Load tenant catalog
    products = list((await db.execute(
        select(Product).where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
    )).scalars().all())
    if not products:
        logger.info("interest_infer: no catalog products for tenant=%s", str(tenant_id)[:8])
        return []

    ports = list((await db.execute(select(Port))).scalars().all())
    port_map = {p.name.lower(): p for p in ports}

    # Load existing interests to avoid duplicates
    existing = list((await db.execute(
        select(ProductPortInterest).where(
            ProductPortInterest.tenant_id == tenant_id,
            ProductPortInterest.company_id == company_id,
        )
    )).scalars().all())
    existing_keys = set()
    for e in existing:
        key = (str(e.product_id), str(e.destination_port_id or ""), e.role.value)
        existing_keys.add(key)

    candidates = []

    # ── Source 1: Shipment data ──────────────────────────────────────
    shipments = list((await db.execute(
        select(Shipment).where(
            Shipment.tenant_id == tenant_id,
            Shipment.company_id == company_id,
        ).order_by(desc(Shipment.shipment_date)).limit(100)
    )).scalars().all())

    if shipments:
        # Group by commodity+port
        from collections import defaultdict
        ship_groups = defaultdict(list)
        for s in shipments:
            key = (s.commodity_text, s.destination_port_text or "", s.direction.value)
            ship_groups[key].append(s)

        for (commodity, port_text, direction), group in ship_groups.items():
            pid, conf = match_commodity_to_catalog(commodity, products)
            if not pid:
                continue

            # Find port
            dest_port_id = None
            if port_text:
                port_obj = port_map.get(port_text.lower())
                if port_obj:
                    dest_port_id = port_obj.id

            role = InterestRole.buyer if direction == "import" else InterestRole.seller
            count = len(group)
            total_vol = sum(float(s.volume_mt or 0) for s in group)
            last_date = max(s.shipment_date for s in group)

            # Confidence based on shipment count
            if count >= 3:
                base_conf = 0.9
            elif count >= 1:
                base_conf = 0.7
            else:
                base_conf = 0.5

            check_key = (pid, str(dest_port_id or ""), role.value)
            if check_key in existing_keys:
                continue

            candidates.append({
                "product_id": uuid.UUID(pid),
                "destination_port_id": dest_port_id,
                "role": role,
                "source": InterestSource.shipment_data,
                "confidence": base_conf,
                "evidence": {
                    "type": "shipment",
                    "count": count,
                    "volume_mt": total_vol,
                    "last_shipment_date": last_date.isoformat(),
                    "explanation": f"{count} shipments of {commodity}, {total_vol:.0f} MT total, last {last_date.isoformat()}",
                },
            })

    # ── Source 2: Company enrichment data (commodities field) ────────
    if company.commodities:
        for comm in company.commodities:
            pid, conf = match_commodity_to_catalog(comm, products)
            if not pid:
                continue

            # Find destination port from company
            dest_port_id = None
            if company.destination_ports:
                for dp in company.destination_ports:
                    port_obj = port_map.get(dp.lower())
                    if port_obj:
                        dest_port_id = port_obj.id
                        break

            check_key = (pid, str(dest_port_id or ""), "buyer")
            if check_key in existing_keys:
                continue

            candidates.append({
                "product_id": uuid.UUID(pid),
                "destination_port_id": dest_port_id,
                "role": InterestRole.buyer,
                "source": InterestSource.enrichment,
                "confidence": 0.4,
                "evidence": {
                    "type": "enrichment",
                    "field": "company.commodities",
                    "value": comm,
                    "explanation": f"Company profile lists '{comm}' as a traded commodity",
                },
            })

    # ── Source 3: AI analysis of message threads ─────────────────────
    messages = list((await db.execute(
        select(Message).where(
            Message.tenant_id == tenant_id,
            Message.contact_id.in_(
                select(Contact.id).where(Contact.company_id == company_id, Contact.tenant_id == tenant_id)
            ),
        ).order_by(desc(Message.created_at)).limit(20)
    )).scalars().all())

    if messages and len(messages) >= 2:
        # Build thread context for AI
        thread_text = "\n".join([
            f"{'BUYER' if m.direction == MessageDirection.inbound else 'US'}: {(m.body or '')[:200]}"
            for m in messages[:10]
        ])

        product_names = [p.name for p in products]
        port_names = [p.name for p in ports]

        try:
            prompt = f"""Analyze this trade conversation and identify which products the buyer is interested in.

Available products in our catalog: {', '.join(product_names)}
Known ports: {', '.join(port_names[:20])}

Conversation:
{thread_text}

Return JSON array of interests found:
[{{"product": "exact product name from catalog", "destination_port": "port name or null", "confidence": 0.5-0.9, "evidence": "one-line quote from conversation"}}]

Only include products that appear in our catalog list above. Return empty array if no matches."""

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
                    json={
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            raw = extract_gemini_text(parts)
            parsed = safe_parse_json(raw, fallback=[])

            if isinstance(parsed, list):
                for item in parsed:
                    pname = item.get("product", "")
                    pid, _ = match_commodity_to_catalog(pname, products)
                    if not pid:
                        continue

                    dest_port_id = None
                    dp_name = item.get("destination_port")
                    if dp_name:
                        port_obj = port_map.get(dp_name.lower())
                        if port_obj:
                            dest_port_id = port_obj.id

                    ai_conf = min(0.85, max(0.5, item.get("confidence", 0.6)))
                    check_key = (pid, str(dest_port_id or ""), "buyer")
                    if check_key in existing_keys:
                        continue

                    candidates.append({
                        "product_id": uuid.UUID(pid),
                        "destination_port_id": dest_port_id,
                        "role": InterestRole.buyer,
                        "source": InterestSource.email_thread,
                        "confidence": ai_conf,
                        "evidence": {
                            "type": "email_thread",
                            "message_count": len(messages),
                            "explanation": item.get("evidence", f"Mentioned '{pname}' in conversation"),
                        },
                    })

        except Exception as e:
            logger.error("interest_infer: AI thread analysis failed: %s", str(e), exc_info=True)

    # ── Create interest rows ─────────────────────────────────────────
    created = []
    for c in candidates:
        interest = ProductPortInterest(
            tenant_id=tenant_id,
            company_id=company_id,
            product_id=c["product_id"],
            destination_port_id=c.get("destination_port_id"),
            role=c["role"],
            source=c["source"],
            confidence=c["confidence"],
            confidence_level=_confidence_level(c["confidence"]),
            evidence=c["evidence"],
            status=InterestStatus.suggested,
        )
        db.add(interest)
        created.append({
            "product_id": str(c["product_id"]),
            "source": c["source"].value,
            "confidence": c["confidence"],
        })

    if created:
        await db.flush()
        logger.info("interest_infer: company=%s created %d suggestions", str(company_id)[:8], len(created))

    return created
