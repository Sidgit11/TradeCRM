"""Lead processing pipeline — reads emails, classifies, extracts, matches, stores."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.leads import InboundLead, LeadPreferences
from app.models.email_account import EmailAccount
from app.models.contact import Contact
from app.models.company import Company
from app.models.catalog import Product
from app.models.tenant import Tenant
from app.integrations import gmail_service
from app.agents.lead_classifier import (
    classify_email, match_products_to_catalog, match_to_existing_contacts,
    should_skip_email,
)

logger = get_logger("services.lead_processor")


async def get_catalog_for_classification(db: AsyncSession, tenant_id: uuid.UUID) -> List[Dict]:
    """Get catalog products with varieties, grades, aliases for classification prompt."""
    result = await db.execute(
        select(Product).where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
    )
    products = []
    for p in result.scalars().all():
        varieties = []
        for v in (p.varieties or []):
            grades = [{"id": str(g.id), "name": g.name} for g in (v.grades or [])]
            varieties.append({"name": v.name, "grades": grades})
        products.append({
            "id": str(p.id), "name": p.name, "origin_country": p.origin_country,
            "aliases": p.aliases or [], "varieties": varieties,
        })
    return products


async def get_existing_contacts_and_companies(db: AsyncSession, tenant_id: uuid.UUID):
    """Get existing CRM data for matching."""
    contacts_result = await db.execute(
        select(Contact).where(Contact.tenant_id == tenant_id, Contact.is_deleted.is_(False))
    )
    contacts = [
        {"id": str(c.id), "name": c.name, "email": c.email, "phone": c.phone,
         "company_id": str(c.company_id) if c.company_id else None}
        for c in contacts_result.scalars().all()
    ]

    companies_result = await db.execute(
        select(Company).where(Company.tenant_id == tenant_id, Company.is_deleted.is_(False))
    )
    companies = [{"id": str(c.id), "name": c.name} for c in companies_result.scalars().all()]

    return contacts, companies


async def get_preferences(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[Dict]:
    """Load tenant's lead preferences."""
    result = await db.execute(
        select(LeadPreferences).where(LeadPreferences.tenant_id == tenant_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        return None
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
        "custom_reply_instructions": prefs.custom_reply_instructions,
    }


async def process_email(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email_account_id: uuid.UUID,
    message_data: Dict[str, Any],
    catalog_products: List[Dict],
    existing_contacts: List[Dict],
    existing_companies: List[Dict],
    preferences: Optional[Dict],
    tenant_name: str,
    tenant_commodities: List[str],
) -> Optional[InboundLead]:
    """Process a single email: classify, extract, match, store."""

    gmail_message_id = message_data.get("id", "")
    gmail_thread_id = message_data.get("thread_id", "")
    sender_email = message_data.get("from", "")
    subject = message_data.get("subject", "")
    body = message_data.get("body_text", "") or message_data.get("snippet", "")
    received_at = message_data.get("date", "")

    log_ctx = f"msg={gmail_message_id[:12]} from={sender_email[:40]} subj={subject[:40]}"

    # Check if already processed (dedup by thread)
    existing = await db.execute(
        select(InboundLead).where(
            InboundLead.tenant_id == tenant_id,
            InboundLead.gmail_thread_id == gmail_thread_id,
        )
    )
    existing_lead = existing.scalar_one_or_none()

    if existing_lead:
        existing_lead.thread_message_count = (existing_lead.thread_message_count or 1) + 1
        existing_lead.body_full = body[:5000]
        await db.commit()
        logger.info("process_email: THREAD_UPDATE | thread=%s count=%d | %s", gmail_thread_id[:12], existing_lead.thread_message_count, log_ctx)
        return existing_lead

    # Step 1: Quick filter (sender patterns)
    skip_reason = should_skip_email(sender_email, subject)
    if skip_reason:
        logger.info("process_email: SKIP_PREFILTER | reason=%s | %s", skip_reason, log_ctx)
        return None

    # Step 1b: Body filter (unsubscribe = marketing)
    body_lower = body.lower() if body else ""
    if "unsubscribe" in body_lower and ("click here" in body_lower or "opt out" in body_lower):
        logger.info("process_email: SKIP_MARKETING | unsubscribe_in_body | %s", log_ctx)
        return None

    # Step 2: Classify with Gemini
    logger.info("process_email: CLASSIFY_START | body_len=%d catalog_count=%d | %s", len(body), len(catalog_products), log_ctx)
    classification = await classify_email(
        email_from=sender_email, subject=subject, body=body,
        tenant_name=tenant_name, tenant_commodities=tenant_commodities,
        catalog_products=catalog_products, preferences=preferences,
    )
    logger.info("process_email: CLASSIFY_DONE | cls=%s conf=%s products=%s phone=%s company=%s | %s",
        classification.get("classification"), classification.get("confidence"),
        classification.get("products_mentioned"), classification.get("sender_phone"),
        classification.get("sender_company"), log_ctx)

    # Step 3: Match products to catalog
    products_mentioned = classification.get("products_mentioned", [])
    product_matches = match_products_to_catalog(products_mentioned, catalog_products)
    if product_matches:
        matched_names = [f"{m.get('matched_product_name','?')}({m.get('confidence',0):.0%})" for m in product_matches]
        logger.info("process_email: CATALOG_MATCH | matches=%s | %s", matched_names, log_ctx)
    elif products_mentioned:
        logger.info("process_email: CATALOG_NO_MATCH | raw_products=%s | %s", products_mentioned, log_ctx)

    # Step 4: Match to existing CRM data
    extracted_email = sender_email.split("<")[-1].strip(">").strip() if "<" in sender_email else sender_email
    crm_match = match_to_existing_contacts(
        sender_email=extracted_email,
        sender_name=classification.get("sender_name"),
        sender_company=classification.get("sender_company"),
        existing_contacts=existing_contacts, existing_companies=existing_companies,
        sender_phone=classification.get("sender_phone"),
    )
    if crm_match.get("matched_contact_id") or crm_match.get("matched_company_id"):
        logger.info("process_email: CRM_MATCH | contact=%s(%.0f%%) company=%s(%.0f%%) | %s",
            crm_match.get("matched_contact_id", "none")[:8] if crm_match.get("matched_contact_id") else "none",
            (crm_match.get("matched_contact_confidence") or 0) * 100,
            crm_match.get("matched_company_id", "none")[:8] if crm_match.get("matched_company_id") else "none",
            (crm_match.get("matched_company_confidence") or 0) * 100,
            log_ctx)

    # Step 5: Apply preference rules
    is_high_value = False
    if preferences:
        qty_values = [q.get("value", 0) for q in classification.get("quantities", []) if q.get("value")]
        max_qty = max(qty_values) if qty_values else 0
        if preferences.get("high_value_threshold_mt") and max_qty >= preferences["high_value_threshold_mt"]:
            is_high_value = True
            logger.info("process_email: HIGH_VALUE | qty=%s threshold=%s | %s",
                max_qty, preferences["high_value_threshold_mt"], log_ctx)

    clean_email = extracted_email

    # Step 6: Store
    lead = InboundLead(
        tenant_id=tenant_id, email_account_id=email_account_id,
        gmail_message_id=gmail_message_id, gmail_thread_id=gmail_thread_id,
        classification=classification.get("classification", "lead"),
        non_lead_reason=classification.get("non_lead_reason"),
        confidence=classification.get("confidence", 0.5),
        sender_name=classification.get("sender_name") or sender_email.split("<")[0].strip().strip('"'),
        sender_email=clean_email,
        sender_phone=classification.get("sender_phone"),
        sender_company=classification.get("sender_company"),
        sender_designation=classification.get("sender_designation"),
        matched_contact_id=uuid.UUID(crm_match["matched_contact_id"]) if crm_match.get("matched_contact_id") else None,
        matched_contact_confidence=crm_match.get("matched_contact_confidence"),
        matched_company_id=uuid.UUID(crm_match["matched_company_id"]) if crm_match.get("matched_company_id") else None,
        matched_company_confidence=crm_match.get("matched_company_confidence"),
        subject=subject,
        body_preview=body[:500] if body else None,
        body_full=body[:5000] if body else None,
        thread_message_count=1,
        products_mentioned=product_matches if product_matches else None,
        quantities=classification.get("quantities") or None,
        target_price=classification.get("target_price"),
        delivery_terms=classification.get("delivery_terms"),
        destination=classification.get("destination"),
        urgency=classification.get("urgency"),
        specific_questions=classification.get("specific_questions"),
        language=classification.get("language"),
        status="new", is_high_value=is_high_value,
    )

    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    logger.info("process_email: STORED | id=%s cls=%s conf=%.2f high_value=%s | %s",
        str(lead.id)[:8], lead.classification, float(lead.confidence or 0), is_high_value, log_ctx)
    return lead


async def process_account_emails(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email_account_id: uuid.UUID,
) -> Dict[str, int]:
    """Process all new emails from a connected account. Returns counts."""
    logger.info("sync: START | tenant=%s account=%s", str(tenant_id)[:8], str(email_account_id)[:8])

    account = (await db.execute(
        select(EmailAccount).where(EmailAccount.id == email_account_id, EmailAccount.is_active.is_(True))
    )).scalar_one_or_none()
    if not account or not account.token_data:
        logger.error("sync: ABORT | account not found or no tokens | account=%s", str(email_account_id)[:8])
        return {"error": "Account not found or not connected"}

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    tenant_name = tenant.company_name
    tenant_commodities = tenant.commodities or []

    catalog = await get_catalog_for_classification(db, tenant_id)
    contacts, companies = await get_existing_contacts_and_companies(db, tenant_id)
    prefs = await get_preferences(db, tenant_id)
    logger.info("sync: CONTEXT_LOADED | account=%s catalog=%d contacts=%d companies=%d prefs=%s",
        account.email_address, len(catalog), len(contacts), len(companies), "custom" if prefs else "defaults")

    messages_result = gmail_service.list_messages(account.token_data, query="newer_than:7d", max_results=50)
    message_refs = messages_result.get("messages", [])
    logger.info("sync: EMAILS_FETCHED | count=%d account=%s", len(message_refs), account.email_address)

    leads_created = 0
    non_leads = 0
    skipped = 0

    for ref in message_refs:
        msg_id = ref["id"]

        # Check if already processed
        existing = await db.execute(
            select(InboundLead).where(
                InboundLead.tenant_id == tenant_id,
                InboundLead.gmail_message_id == msg_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Fetch full message
        try:
            msg_data = gmail_service.get_message(account.token_data, msg_id)
        except Exception as e:
            logger.error("Failed to fetch message %s: %s", msg_id, str(e))
            continue

        # Skip if sent by the user themselves
        if account.email_address.lower() in msg_data.get("from", "").lower():
            skipped += 1
            continue

        # Process
        lead = await process_email(
            db=db, tenant_id=tenant_id, email_account_id=email_account_id,
            message_data=msg_data, catalog_products=catalog,
            existing_contacts=contacts, existing_companies=companies,
            preferences=prefs, tenant_name=tenant_name,
            tenant_commodities=tenant_commodities,
        )

        if lead:
            if lead.classification == "lead":
                leads_created += 1
            else:
                non_leads += 1
        else:
            skipped += 1

    # Update last sync
    account.last_sync_at = datetime.now(timezone.utc).isoformat()
    await db.commit()

    logger.info(
        "Account sync complete: account=%s leads=%d non_leads=%d skipped=%d",
        account.email_address, leads_created, non_leads, skipped,
    )
    return {"leads": leads_created, "non_leads": non_leads, "skipped": skipped, "total_checked": len(message_refs)}
