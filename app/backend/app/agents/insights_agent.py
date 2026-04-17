"""AI Insights Agent — generates deal-actionable nudges for companies, contacts, opportunities, and leads.

Analyzes all available data (shipments, interests, messages, opportunities, leads, enrichment)
and produces 2-5 short, specific, actionable insights with CTAs.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import httpx
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging_config import get_logger
from app.utils.gemini import safe_parse_json, GEMINI_URL, extract_gemini_text
from app.models.company import Company
from app.models.contact import Contact
from app.models.message import Message
from app.models.pipeline import PipelineOpportunity
from app.models.leads import InboundLead
from app.models.shipment import Shipment
from app.models.shipment_summary import CompanyShipmentSummary
from app.models.product_port_interest import ProductPortInterest
from app.models.enums import MessageDirection, InterestStatus

logger = get_logger("agents.insights")


async def _gather_company_context(db: AsyncSession, tenant_id: uuid.UUID, company_id: uuid.UUID) -> Dict:
    """Gather all relevant data about a company for insight generation."""
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        return {}

    # Contacts
    contacts = list((await db.execute(
        select(Contact).where(Contact.company_id == company_id, Contact.tenant_id == tenant_id, Contact.is_deleted.is_(False))
    )).scalars().all())

    # Recent messages (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    contact_ids = [c.id for c in contacts]
    messages = []
    if contact_ids:
        messages = list((await db.execute(
            select(Message).where(
                Message.tenant_id == tenant_id,
                Message.contact_id.in_(contact_ids),
            ).order_by(desc(Message.created_at)).limit(20)
        )).scalars().all())

    # Active opportunities
    opps = list((await db.execute(
        select(PipelineOpportunity).where(
            PipelineOpportunity.company_id == company_id,
            PipelineOpportunity.tenant_id == tenant_id,
            PipelineOpportunity.is_archived.is_(False),
        )
    )).scalars().all())

    # Active leads
    leads = list((await db.execute(
        select(InboundLead).where(
            InboundLead.company_id == company_id,
            InboundLead.tenant_id == tenant_id,
            InboundLead.status.notin_(["dismissed"]),
        ).order_by(desc(InboundLead.created_at)).limit(5)
    )).scalars().all())

    # Shipment summary
    ship_summary = (await db.execute(
        select(CompanyShipmentSummary).where(
            CompanyShipmentSummary.company_id == company_id,
            CompanyShipmentSummary.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    # Interests
    interests = list((await db.execute(
        select(ProductPortInterest).where(
            ProductPortInterest.company_id == company_id,
            ProductPortInterest.tenant_id == tenant_id,
            ProductPortInterest.status == InterestStatus.confirmed,
        )
    )).scalars().all())

    # Compute derived facts
    now = datetime.now(timezone.utc)
    last_outbound = None
    last_inbound = None
    unanswered_inbound = False
    for m in messages:
        if m.direction == MessageDirection.outbound and not last_outbound:
            last_outbound = m
        if m.direction == MessageDirection.inbound and not last_inbound:
            last_inbound = m

    if last_inbound and (not last_outbound or last_inbound.created_at > last_outbound.created_at):
        unanswered_inbound = True

    days_since_contact = None
    if last_outbound:
        days_since_contact = (now - last_outbound.created_at).days
    elif company.last_interaction_at:
        days_since_contact = (now - company.last_interaction_at).days

    pending_leads = [l for l in leads if l.status in ("new", "reviewed")]
    sample_opps = [o for o in opps if o.sample_sent and o.sample_approved is None]

    return {
        "company_name": company.name,
        "company_country": company.country,
        "company_type": company.company_type,
        "rating": company.rating,
        "commodities": company.commodities or [],
        "contacts": [{"name": c.name, "title": c.title, "email": c.email} for c in contacts[:5]],
        "days_since_contact": days_since_contact,
        "unanswered_inbound": unanswered_inbound,
        "last_inbound_preview": (last_inbound.body[:100] if last_inbound and last_inbound.body else None),
        "last_inbound_date": last_inbound.created_at.isoformat() if last_inbound else None,
        "message_count_30d": len(messages),
        "active_opportunities": len(opps),
        "opp_details": [{"title": o.title, "commodity": o.commodity, "stage_name": None, "sample_sent": o.sample_sent, "sample_approved": o.sample_approved, "follow_up_date": o.follow_up_date.isoformat() if o.follow_up_date else None} for o in opps[:5]],
        "pending_leads": len(pending_leads),
        "lead_subjects": [l.subject for l in pending_leads[:3]],
        "shipments_12mo": ship_summary.shipments_12mo if ship_summary else 0,
        "volume_12mo_mt": float(ship_summary.volume_12mo_mt or 0) if ship_summary else 0,
        "avg_price": float(ship_summary.avg_unit_price_usd_per_mt or 0) if ship_summary else 0,
        "confirmed_interests": len(interests),
        "sample_awaiting_feedback": len(sample_opps),
    }


async def generate_insights(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
) -> List[Dict]:
    """Generate deal-actionable insights for an entity.

    Args:
        entity_type: "company", "contact", "opportunity", or "lead"
        entity_id: The entity's UUID

    Returns:
        List of insight dicts: [{icon, title, body, action_label, action_type, priority}]
    """
    # Gather context based on entity type
    if entity_type == "company":
        context = await _gather_company_context(db, tenant_id, entity_id)
    elif entity_type == "contact":
        contact = (await db.execute(select(Contact).where(Contact.id == entity_id))).scalar_one_or_none()
        if contact and contact.company_id:
            context = await _gather_company_context(db, tenant_id, contact.company_id)
            context["focus_contact"] = contact.name
        else:
            context = {"focus_contact": contact.name if contact else "Unknown", "company_name": contact.company_name if contact else None}
    elif entity_type == "opportunity":
        opp = (await db.execute(select(PipelineOpportunity).where(PipelineOpportunity.id == entity_id))).scalar_one_or_none()
        if opp:
            context = await _gather_company_context(db, tenant_id, opp.company_id)
            context["focus_opportunity"] = opp.title or "Untitled"
            context["opp_commodity"] = opp.commodity
            context["opp_stage"] = None
            context["opp_sample_sent"] = opp.sample_sent
            context["opp_sample_approved"] = opp.sample_approved
            context["opp_follow_up"] = opp.follow_up_date.isoformat() if opp.follow_up_date else None
        else:
            context = {}
    elif entity_type == "lead":
        lead = (await db.execute(select(InboundLead).where(InboundLead.id == entity_id))).scalar_one_or_none()
        if lead and lead.company_id:
            context = await _gather_company_context(db, tenant_id, lead.company_id)
            context["focus_lead_subject"] = lead.subject
            context["focus_lead_status"] = lead.status
            context["focus_lead_products"] = lead.products_mentioned
        else:
            context = {"focus_lead_subject": lead.subject if lead else None}
    else:
        context = {}

    if not context:
        return []

    # --- Rule-based insights (fast, no LLM needed) ---
    insights = []

    # 1. Follow-up overdue
    days = context.get("days_since_contact")
    if days and days > 7:
        insights.append({
            "icon": "clock",
            "title": "Follow up overdue",
            "body": f"Last contacted {days} days ago. Don't let this go cold.",
            "action_label": "Draft follow-up",
            "action_type": "draft_followup",
            "priority": 1 if days > 14 else 2,
        })

    # 2. Unanswered inbound
    if context.get("unanswered_inbound"):
        preview = context.get("last_inbound_preview", "")
        insights.append({
            "icon": "warning",
            "title": "Unanswered message",
            "body": f"They sent a message and haven't received a reply yet. \"{preview[:60]}...\"" if preview else "An inbound message is waiting for your reply.",
            "action_label": "Reply now",
            "action_type": "open_inbox",
            "priority": 1,
        })

    # 3. Pending leads
    if context.get("pending_leads", 0) > 0:
        subjects = context.get("lead_subjects", [])
        sub_text = f": \"{subjects[0]}\"" if subjects else ""
        insights.append({
            "icon": "envelope",
            "title": f"{context['pending_leads']} pending lead{'s' if context['pending_leads'] > 1 else ''}",
            "body": f"New inquiry waiting for review{sub_text}.",
            "action_label": "Review leads",
            "action_type": "open_leads",
            "priority": 1,
        })

    # 4. Sample awaiting feedback
    if context.get("sample_awaiting_feedback", 0) > 0:
        insights.append({
            "icon": "package",
            "title": "Sample feedback pending",
            "body": f"{context['sample_awaiting_feedback']} sample{'s' if context['sample_awaiting_feedback'] > 1 else ''} sent but no feedback received yet.",
            "action_label": "Ask for feedback",
            "action_type": "draft_followup",
            "priority": 2,
        })

    # 5. High-volume buyer not in pipeline
    if context.get("shipments_12mo", 0) >= 5 and context.get("active_opportunities", 0) == 0:
        vol = context.get("volume_12mo_mt", 0)
        insights.append({
            "icon": "truck",
            "title": "Active buyer, no deals tracked",
            "body": f"This company had {context['shipments_12mo']} shipments ({vol:.0f} MT) in 12 months but no active opportunities. Create one to track the deal.",
            "action_label": "Create opportunity",
            "action_type": "create_opportunity",
            "priority": 2,
        })

    # 6. No trade interests mapped
    if context.get("confirmed_interests", 0) == 0 and context.get("shipments_12mo", 0) > 0:
        insights.append({
            "icon": "sparkle",
            "title": "Trade interests not mapped",
            "body": "Shipment data exists but no product interests are confirmed. Run AI inference to map what they buy.",
            "action_label": "Discover interests",
            "action_type": "infer_interests",
            "priority": 3,
        })

    # 7. Hot-rated but no recent contact
    if context.get("rating") == "hot" and (days is None or days > 5):
        insights.append({
            "icon": "fire",
            "title": "Hot lead going cold",
            "body": f"{context.get('company_name', 'This company')} is rated hot but hasn't been contacted recently.",
            "action_label": "Reach out",
            "action_type": "draft_followup",
            "priority": 1,
        })

    # --- LLM-powered strategic insight ---
    # Only call LLM if we have enough context and fewer than 4 rule-based insights
    if len(insights) < 4 and (context.get("shipments_12mo", 0) > 0 or context.get("message_count_30d", 0) > 0):
        try:
            ai_insight = await _generate_llm_insight(context, entity_type)
            if ai_insight:
                insights.append(ai_insight)
        except Exception as e:
            logger.error("LLM insight generation failed: %s", str(e), exc_info=True)

    # Sort by priority, cap at 5
    insights.sort(key=lambda x: x["priority"])
    return insights[:5]


async def _generate_llm_insight(context: Dict, entity_type: str) -> Optional[Dict]:
    """Generate one strategic insight using Gemini."""
    import json

    prompt = f"""You are a trade advisor for commodity exporters. Analyze this {entity_type} data and produce ONE actionable insight the exporter should act on.

Data:
- Company: {context.get('company_name', 'Unknown')} ({context.get('company_country', '')}, {context.get('company_type', '')})
- Rating: {context.get('rating', 'none')}
- Commodities of interest: {', '.join(context.get('commodities', []))}
- Shipments (12mo): {context.get('shipments_12mo', 0)} shipments, {context.get('volume_12mo_mt', 0):.0f} MT
- Average price: ${context.get('avg_price', 0):.0f}/MT
- Days since last contact: {context.get('days_since_contact', 'unknown')}
- Active opportunities: {context.get('active_opportunities', 0)}
- Pending leads: {context.get('pending_leads', 0)}
- Messages in last 30 days: {context.get('message_count_30d', 0)}
- Confirmed trade interests: {context.get('confirmed_interests', 0)}

Return ONLY valid JSON:
{{"title": "short title (5-8 words)", "body": "1-2 sentence actionable insight", "action_label": "short CTA button text"}}

Focus on: pricing strategy, timing, relationship building, or competitive positioning. Be specific to commodity trade."""

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 256},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = extract_gemini_text(parts)
    parsed = safe_parse_json(raw, fallback=None)

    if parsed and parsed.get("title") and parsed.get("body"):
        return {
            "icon": "lightbulb",
            "title": parsed["title"],
            "body": parsed["body"],
            "action_label": parsed.get("action_label", "Take action"),
            "action_type": "ai_suggestion",
            "priority": 3,
        }

    return None
