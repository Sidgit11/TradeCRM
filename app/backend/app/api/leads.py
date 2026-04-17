"""Leads API — list, detail, actions, sync, preferences."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.leads import InboundLead, LeadPreferences
from app.models.contact import Contact
from app.models.company import Company
from app.models.enums import ContactSource, CompanySource
from app.services.lead_processor import process_account_emails

logger = get_logger("api.leads")
router = APIRouter(prefix="/leads", tags=["leads"])


# --- Schemas ---

class LeadUpdateRequest(BaseModel):
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    sender_company: Optional[str] = None
    sender_designation: Optional[str] = None
    products_mentioned: Optional[list] = None
    quantities: Optional[list] = None
    target_price: Optional[str] = None
    delivery_terms: Optional[str] = None
    destination: Optional[str] = None
    urgency: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    classification: Optional[str] = None
    non_lead_reason: Optional[str] = None


class PreferencesUpdate(BaseModel):
    ignore_below_qty_mt: Optional[float] = None
    ignore_countries: Optional[list] = None
    auto_non_lead_if_no_catalog_match: Optional[bool] = None
    reply_tone: Optional[str] = None
    reply_language: Optional[str] = None
    include_fob_price: Optional[bool] = None
    include_cfr_quote: Optional[bool] = None
    include_certifications: Optional[bool] = None
    include_moq: Optional[bool] = None
    high_value_threshold_mt: Optional[float] = None
    high_value_reply_style: Optional[str] = None
    custom_reply_instructions: Optional[str] = None


# --- Helpers ---

def _lead_response(lead: InboundLead) -> dict:
    return {
        "id": str(lead.id),
        "classification": lead.classification,
        "non_lead_reason": lead.non_lead_reason,
        "confidence": float(lead.confidence) if lead.confidence else None,
        "sender_name": lead.sender_name,
        "sender_email": lead.sender_email,
        "sender_phone": lead.sender_phone,
        "sender_company": lead.sender_company,
        "sender_designation": lead.sender_designation,
        "matched_contact_id": str(lead.matched_contact_id) if lead.matched_contact_id else None,
        "matched_contact_confidence": float(lead.matched_contact_confidence) if lead.matched_contact_confidence else None,
        "matched_company_id": str(lead.matched_company_id) if lead.matched_company_id else None,
        "matched_company_confidence": float(lead.matched_company_confidence) if lead.matched_company_confidence else None,
        "subject": lead.subject,
        "body_preview": lead.body_preview,
        "received_at": lead.received_at.isoformat() if lead.received_at else lead.created_at.isoformat(),
        "thread_message_count": lead.thread_message_count,
        "products_mentioned": lead.products_mentioned or [],
        "quantities": lead.quantities or [],
        "target_price": lead.target_price,
        "delivery_terms": lead.delivery_terms,
        "destination": lead.destination,
        "urgency": lead.urgency,
        "specific_questions": lead.specific_questions,
        "language": lead.language,
        "status": lead.status,
        "is_high_value": lead.is_high_value,
        "assigned_to": str(lead.assigned_to) if lead.assigned_to else None,
        "contact_id": str(lead.contact_id) if lead.contact_id else None,
        "company_id": str(lead.company_id) if lead.company_id else None,
        "notes": lead.notes,
        "draft_reply": lead.draft_reply,
        "draft_reply_explanation": lead.draft_reply_explanation,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
    }


# --- Sync ---

@router.post("/sync/{account_id}")
async def sync_account_leads(
    account_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Trigger email sync + lead classification for a connected account."""
    result = await process_account_emails(db, tenant_id, account_id)
    return result


# --- List & Detail ---

@router.get("")
async def list_leads(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    tab: str = Query("leads", pattern="^(leads|other|all)$"),
    status_filter: Optional[str] = Query(None, alias="status"),
    urgency: Optional[str] = None,
    search: Optional[str] = None,
    company_id: Optional[uuid.UUID] = None,
    contact_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """List inbound leads. Tab: leads, other, all."""
    query = select(InboundLead).where(InboundLead.tenant_id == tenant_id)

    if company_id:
        query = query.where(InboundLead.company_id == company_id)
    if contact_id:
        query = query.where(InboundLead.contact_id == contact_id)
    if active_only:
        query = query.where(InboundLead.status.notin_(["dismissed", "in_pipeline"]))

    if tab == "leads":
        query = query.where(InboundLead.classification == "lead")
    elif tab == "other":
        query = query.where(InboundLead.classification == "non_lead")

    if status_filter:
        query = query.where(InboundLead.status == status_filter)

    if search:
        term = f"%{search}%"
        from sqlalchemy import or_
        query = query.where(or_(
            InboundLead.sender_name.ilike(term),
            InboundLead.sender_email.ilike(term),
            InboundLead.sender_company.ilike(term),
            InboundLead.subject.ilike(term),
        ))

    if urgency:
        query = query.where(InboundLead.urgency == urgency)

    # Exclude dismissed by default
    if not status_filter:
        query = query.where(InboundLead.status != "dismissed")

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    from sqlalchemy import asc
    sort_col = getattr(InboundLead, sort_by, InboundLead.created_at)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return {
        "items": [_lead_response(l) for l in result.scalars().all()],
        "total": total,
        "tab": tab,
    }


@router.get("/stats")
async def get_lead_stats(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Lead count stats for tabs."""
    leads_count = (await db.execute(
        select(func.count()).where(InboundLead.tenant_id == tenant_id, InboundLead.classification == "lead")
    )).scalar() or 0
    other_count = (await db.execute(
        select(func.count()).where(InboundLead.tenant_id == tenant_id, InboundLead.classification == "non_lead")
    )).scalar() or 0
    new_count = (await db.execute(
        select(func.count()).where(
            InboundLead.tenant_id == tenant_id, InboundLead.classification == "lead",
            InboundLead.status == "new",
        )
    )).scalar() or 0

    return {"leads": leads_count, "other": other_count, "new": new_count, "total": leads_count + other_count}


@router.get("/{lead_id}")
async def get_lead_detail(
    lead_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get full lead detail including body."""
    lead = (await db.execute(
        select(InboundLead).where(InboundLead.id == lead_id, InboundLead.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Auto-mark as reviewed when user opens detail
    if lead.status == "new":
        lead.status = "reviewed"
        await db.commit()
        await db.refresh(lead)

    resp = _lead_response(lead)
    resp["body_full"] = lead.body_full
    return resp


# --- Actions ---

@router.put("/{lead_id}")
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdateRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Update lead fields (user edits/overrides AI)."""
    lead = (await db.execute(
        select(InboundLead).where(InboundLead.id == lead_id, InboundLead.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    await db.commit()
    await db.refresh(lead)

    logger.info("Lead updated: id=%s fields=%s", lead_id, list(body.model_dump(exclude_unset=True).keys()))
    return _lead_response(lead)


@router.post("/{lead_id}/move-to-pipeline")
async def save_lead_to_crm(
    lead_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Create Contact + Company + Pipeline Opportunity from lead data."""
    from app.models.pipeline import PipelineStage, PipelineOpportunity
    from app.models.enums import OpportunitySource
    from app.api.pipeline import _ensure_default_stages, _generate_display_id
    from sqlalchemy import or_

    lead = (await db.execute(
        select(InboundLead).where(InboundLead.id == lead_id, InboundLead.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    logger.info("move_to_pipeline: START | lead=%s sender=%s company=%s", str(lead_id)[:8], lead.sender_email, lead.sender_company)

    # Step 1: Find or create Company
    company_id = lead.company_id
    if not company_id and lead.sender_company:
        # Match by name (case-insensitive)
        existing_co = (await db.execute(
            select(Company).where(
                Company.tenant_id == tenant_id,
                Company.name.ilike(lead.sender_company),
                Company.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if existing_co:
            company_id = existing_co.id
            logger.info("move_to_pipeline: COMPANY_MATCHED | id=%s name=%s", str(company_id)[:8], existing_co.name)
        else:
            # Extract commodities from lead's product mentions
            lead_commodities = []
            if lead.products_mentioned:
                for p in lead.products_mentioned:
                    name_val = p.get("matched_product_name") or p.get("raw")
                    if name_val and name_val not in lead_commodities:
                        lead_commodities.append(name_val)

            company = Company(
                tenant_id=tenant_id,
                name=lead.sender_company,
                country=lead.destination,  # buyer's country often = destination
                commodities=lead_commodities,
                preferred_incoterms=lead.delivery_terms,
                source=CompanySource.discovery,
                first_contact_date=lead.created_at.date() if lead.created_at else None,
                total_inquiries=1,
            )
            db.add(company)
            await db.flush()
            company_id = company.id
            logger.info("move_to_pipeline: COMPANY_CREATED | id=%s name=%s country=%s commodities=%s",
                str(company_id)[:8], lead.sender_company, lead.destination, lead_commodities)

    # Step 2: Find or create Contact (match by email OR phone)
    contact_id = lead.contact_id
    if not contact_id:
        match_conditions = []
        if lead.sender_email:
            match_conditions.append(Contact.email == lead.sender_email)
        if lead.sender_phone:
            match_conditions.append(Contact.phone == lead.sender_phone)

        existing_ct = None
        if match_conditions:
            existing_ct = (await db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.is_deleted.is_(False),
                    or_(*match_conditions),
                )
            )).scalar_one_or_none()

        if existing_ct:
            contact_id = existing_ct.id
            # Update contact with any new info from lead
            if lead.sender_phone and not existing_ct.phone:
                existing_ct.phone = lead.sender_phone
            if lead.sender_designation and not existing_ct.title:
                existing_ct.title = lead.sender_designation
            if company_id and not existing_ct.company_id:
                existing_ct.company_id = company_id
                existing_ct.company_name = lead.sender_company
            logger.info("move_to_pipeline: CONTACT_MATCHED | id=%s name=%s", str(contact_id)[:8], existing_ct.name)
        else:
            from datetime import datetime, timezone as tz
            contact = Contact(
                tenant_id=tenant_id,
                name=lead.sender_name or lead.sender_email,
                email=lead.sender_email,
                phone=lead.sender_phone,
                whatsapp_number=lead.sender_phone,  # assume phone = WA for now
                company_name=lead.sender_company,
                company_id=company_id,
                title=lead.sender_designation,
                preferred_language=lead.language,
                source=ContactSource.discovery,
                first_seen_at=lead.created_at,
            )
            db.add(contact)
            await db.flush()
            contact_id = contact.id
            logger.info("move_to_pipeline: CONTACT_CREATED | id=%s name=%s email=%s phone=%s",
                str(contact_id)[:8], lead.sender_name, lead.sender_email, lead.sender_phone)

    lead.contact_id = contact_id
    lead.company_id = company_id
    lead.status = "in_pipeline"
    await db.flush()

    # Step 3: Create Pipeline Opportunity (always — even without company)
    stages = await _ensure_default_stages(db, tenant_id)
    stage = stages[0] if stages else None

    opportunity_id = None
    if stage:
        # If no company, create a placeholder company from sender info
        if not company_id:
            placeholder_name = lead.sender_company or f"{lead.sender_name or lead.sender_email} (Lead)"
            company = Company(tenant_id=tenant_id, name=placeholder_name, source=CompanySource.discovery)
            db.add(company)
            await db.flush()
            company_id = company.id
            lead.company_id = company_id
            logger.info("move_to_pipeline: PLACEHOLDER_COMPANY | id=%s name=%s", str(company_id)[:8], placeholder_name)

        # Extract commodity from products mentioned
        commodity = None
        if lead.products_mentioned:
            first_product = lead.products_mentioned[0]
            commodity = first_product.get("matched_product_name") or first_product.get("raw")

        # Extract deal details from lead
        quantity = None
        if lead.quantities:
            qty_values = [q.get("value") for q in lead.quantities if q.get("value")]
            quantity = qty_values[0] if qty_values else None

        product_id = None
        grade_id = None
        if lead.products_mentioned:
            first = lead.products_mentioned[0]
            product_id = first.get("matched_product_id")
            grade_id = first.get("matched_grade_id")
            if product_id:
                try:
                    product_id = uuid.UUID(product_id)
                except (ValueError, TypeError):
                    product_id = None

        # Auto-generate title: CompanyName_ContactFirstName_Commodity_Date
        from datetime import date as _date
        company_short = (lead.sender_company or "Unknown")[:7]
        contact_first = (lead.sender_name or "").split()[0][:7] if lead.sender_name else ""
        commodity_short = (commodity or "")[:7]
        date_str = _date.today().strftime("%d%b")
        title_parts = [p for p in [company_short, contact_first, commodity_short, date_str] if p]
        auto_title = "_".join(title_parts)

        display_id = await _generate_display_id(db, tenant_id)

        opp = PipelineOpportunity(
            tenant_id=tenant_id,
            company_id=company_id,
            contact_id=contact_id,
            lead_id=lead.id,
            stage_id=stage.id,
            display_id=display_id,
            title=auto_title,
            source=OpportunitySource.inbound_email,
            commodity=commodity,
            product_id=product_id,
            quantity_mt=quantity,
            incoterms=lead.delivery_terms,
            notes=f"From lead: {lead.subject or '(no subject)'}",
        )
        db.add(opp)
        await db.flush()
        opportunity_id = str(opp.id)
        logger.info("move_to_pipeline: OPPORTUNITY_CREATED | id=%s stage=%s commodity=%s", str(opp.id)[:8], stage.name, commodity)

    await db.commit()

    logger.info("move_to_pipeline: DONE | lead=%s contact=%s company=%s opp=%s",
        str(lead_id)[:8], str(contact_id)[:8] if contact_id else "none",
        str(company_id)[:8] if company_id else "none", opportunity_id[:8] if opportunity_id else "none")

    return {
        "contact_id": str(contact_id) if contact_id else None,
        "company_id": str(company_id) if company_id else None,
        "opportunity_id": opportunity_id,
        "status": "in_pipeline",
    }


@router.post("/{lead_id}/dismiss")
async def dismiss_lead(
    lead_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    lead = (await db.execute(
        select(InboundLead).where(InboundLead.id == lead_id, InboundLead.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = "dismissed"
    await db.commit()
    return {"status": "dismissed"}


# --- Draft Reply ---

class DraftReplyRequest(BaseModel):
    user_instruction: str = ""
    channel: str = "email"  # "email" or "whatsapp"


class SendReplyRequest(BaseModel):
    body_html: str
    subject: Optional[str] = None


@router.post("/{lead_id}/draft-reply")
async def generate_draft_reply(
    lead_id: uuid.UUID,
    body: DraftReplyRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI draft reply for a lead using Gemini + catalog + preferences."""
    from app.models.tenant import Tenant
    from app.models.catalog import Product, FobPrice, Port
    from app.agents.reply_drafter import draft_reply
    from app.services.lead_processor import get_preferences, get_catalog_for_classification

    lead = (await db.execute(
        select(InboundLead).where(InboundLead.id == lead_id, InboundLead.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    prefs = await get_preferences(db, tenant_id)
    catalog = await get_catalog_for_classification(db, tenant_id)

    # Build catalog context string
    catalog_lines = []
    for p in catalog:
        line = f"- {p['name']} (origin: {p.get('origin_country', '?')})"
        for v in p.get("varieties", []):
            for g in v.get("grades", []):
                line += f"\n  Grade: {g['name']}"
        catalog_lines.append(line)
    catalog_context = "\n".join(catalog_lines) or "No products in catalog."

    # Get latest FOB prices
    pricing_lines = []
    prices_result = await db.execute(
        select(FobPrice).where(FobPrice.tenant_id == tenant_id).order_by(desc(FobPrice.price_date)).limit(10)
    )
    for fp in prices_result.scalars().all():
        port = (await db.execute(select(Port).where(Port.id == fp.origin_port_id))).scalar_one_or_none()
        price_str = f"${float(fp.price_usd_per_mt)}/MT" if fp.price_usd_per_mt else f"${float(fp.price_usd_per_kg)}/kg" if fp.price_usd_per_kg else "N/A"
        pricing_lines.append(f"- FOB {port.name if port else '?'}: {price_str} (as of {fp.price_date})")
    pricing_context = "\n".join(pricing_lines) or "No pricing data available yet."

    lead_data = {
        "sender_name": lead.sender_name, "sender_email": lead.sender_email,
        "sender_company": lead.sender_company, "sender_designation": lead.sender_designation,
        "subject": lead.subject, "body_preview": lead.body_preview,
        "products_mentioned": lead.products_mentioned or [],
        "quantities": lead.quantities or [],
        "delivery_terms": lead.delivery_terms, "destination": lead.destination,
        "urgency": lead.urgency, "specific_questions": lead.specific_questions,
        "is_high_value": lead.is_high_value,
    }

    result = await draft_reply(
        lead_data=lead_data,
        tenant_profile={"company_name": tenant.company_name, "commodities": tenant.commodities or []},
        catalog_context=catalog_context,
        pricing_context=pricing_context,
        preferences=prefs,
        user_instruction=body.user_instruction,
        channel=body.channel,
    )

    # Save draft to lead
    lead.draft_reply = result.get("draft", "")
    lead.draft_reply_explanation = result.get("explanation", "")
    await db.commit()

    logger.info("Draft reply generated for lead=%s", lead_id)
    return {
        "subject": result.get("subject", ""),
        "draft": result.get("draft", ""),
        "explanation": result.get("explanation", ""),
    }


@router.post("/{lead_id}/send-reply")
async def send_lead_reply(
    lead_id: uuid.UUID,
    body: SendReplyRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Send a reply to the lead's email via the connected Gmail account."""
    from app.models.email_account import EmailAccount
    from app.integrations import gmail_service

    lead = (await db.execute(
        select(InboundLead).where(InboundLead.id == lead_id, InboundLead.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get the email account this lead came from
    account = (await db.execute(
        select(EmailAccount).where(EmailAccount.id == lead.email_account_id, EmailAccount.is_active.is_(True))
    )).scalar_one_or_none()
    if not account or not account.token_data:
        raise HTTPException(status_code=400, detail="Email account not connected")

    # Send reply in the same thread
    subject = body.subject or f"Re: {lead.subject or ''}"
    result = gmail_service.send_email(
        token_data=account.token_data,
        to=lead.sender_email,
        subject=subject,
        body_html=body.body_html,
        thread_id=lead.gmail_thread_id,
        in_reply_to=lead.gmail_message_id,
    )

    # Update lead status
    lead.status = "replied"
    await db.commit()

    logger.info("Reply sent for lead=%s to=%s", lead_id, lead.sender_email)
    return {"status": "sent", "gmail_message_id": result.get("id", ""), "thread_id": result.get("thread_id", "")}


# --- Preferences ---

@router.get("/preferences/current")
async def get_preferences(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LeadPreferences).where(LeadPreferences.tenant_id == tenant_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        return {
            "ignore_below_qty_mt": 1.0,
            "ignore_countries": [],
            "auto_non_lead_if_no_catalog_match": True,
            "reply_tone": "formal",
            "reply_language": "match_sender",
            "include_fob_price": True,
            "include_cfr_quote": True,
            "include_certifications": True,
            "include_moq": True,
            "high_value_threshold_mt": 10.0,
            "high_value_reply_style": None,
            "custom_reply_instructions": None,
            "_is_default": True,
        }
    return {
        "ignore_below_qty_mt": float(prefs.ignore_below_qty_mt) if prefs.ignore_below_qty_mt else None,
        "ignore_countries": prefs.ignore_countries or [],
        "auto_non_lead_if_no_catalog_match": prefs.auto_non_lead_if_no_catalog_match,
        "reply_tone": prefs.reply_tone,
        "reply_language": prefs.reply_language,
        "include_fob_price": prefs.include_fob_price,
        "include_cfr_quote": prefs.include_cfr_quote,
        "include_certifications": prefs.include_certifications,
        "include_moq": prefs.include_moq,
        "high_value_threshold_mt": float(prefs.high_value_threshold_mt) if prefs.high_value_threshold_mt else None,
        "high_value_reply_style": prefs.high_value_reply_style,
        "custom_reply_instructions": prefs.custom_reply_instructions,
        "_is_default": False,
    }


@router.put("/preferences/current")
async def update_preferences(
    body: PreferencesUpdate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LeadPreferences).where(LeadPreferences.tenant_id == tenant_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = LeadPreferences(tenant_id=tenant_id)
        db.add(prefs)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)

    logger.info("Lead preferences updated: tenant=%s", tenant_id)
    return {"status": "saved"}
