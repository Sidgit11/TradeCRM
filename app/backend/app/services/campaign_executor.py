"""Campaign execution — sends messages to all recipients when campaign is activated."""
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.campaign import Campaign, CampaignStep
from app.models.contact import Contact, ContactList, ContactListMember
from app.models.message import Message
from app.models.message_template import MessageTemplate
from app.models.company import Company
from app.models.tenant import Tenant
from app.models.enums import ChannelType, MessageDirection, MessageStatus
from app.integrations.gupshup_direct import gupshup_direct
from app.integrations.email_provider import get_email_provider
from app.services.template_variables import resolve_variables

logger = get_logger("services.campaign_executor")


def personalize_message(template: str, contact: Contact, tenant_name: str = "", tenant: Optional[object] = None) -> str:
    """Replace {{variables}} in template with contact data.

    Supports both legacy variables ({{name}}, {{company}}) and canonical
    variables ({{contact_first_name}}, {{company_name}}).
    """
    # First: resolve canonical variables via the registry
    text = resolve_variables(template, contact=contact, tenant=tenant)

    # Legacy compat: resolve old-style variables
    name = contact.name or ""
    first_name = name.split(" ")[0] if name else ""

    text = text.replace("{{1}}", first_name)
    text = text.replace("{{2}}", tenant_name)
    text = text.replace("{{3}}", contact.company_name or "")
    text = text.replace("{{name}}", first_name)
    text = text.replace("{{full_name}}", name)
    text = text.replace("{{company}}", contact.company_name or "")
    text = text.replace("{{email}}", contact.email or "")
    text = text.replace("{{phone}}", contact.phone or "")
    text = text.replace("{{commodity}}", "")

    # Clean any remaining {{variables}}
    text = re.sub(r'\{\{\w+\}\}', '', text)
    return text.strip()


async def get_campaign_contacts(
    db: AsyncSession,
    campaign: Campaign,
    tenant_id: uuid.UUID,
) -> List[Contact]:
    """Get all contacts for a campaign (from contact list or all contacts)."""
    contacts = []

    if campaign.contact_list_id:
        # Get contacts from the list
        result = await db.execute(
            select(Contact)
            .join(ContactListMember, ContactListMember.contact_id == Contact.id)
            .where(
                ContactListMember.contact_list_id == campaign.contact_list_id,
                Contact.is_deleted.is_(False),
            )
        )
        contacts = list(result.scalars().all())
    else:
        # If no list, get all tenant contacts with phone (for WA) or email
        result = await db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.is_deleted.is_(False),
            )
        )
        contacts = list(result.scalars().all())

    return contacts


async def execute_campaign(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID,
    contact_ids: Optional[List[uuid.UUID]] = None,
) -> Dict[str, int]:
    """Execute a campaign — send step 1 messages to contacts."""
    from app.models.tenant import Tenant

    campaign = (await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not campaign:
        return {"error": "Campaign not found"}
    if not campaign.steps:
        return {"error": "Campaign has no steps"}

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()

    if contact_ids:
        # Send to specific contacts only
        result = await db.execute(
            select(Contact).where(
                Contact.id.in_(contact_ids),
                Contact.tenant_id == tenant_id,
                Contact.is_deleted.is_(False),
            )
        )
        contacts = list(result.scalars().all())
    else:
        contacts = await get_campaign_contacts(db, campaign, tenant_id)

    if not contacts:
        return {"error": "No contacts found for this campaign"}

    # Get first step
    first_step = sorted(campaign.steps, key=lambda s: s.step_number)[0]

    # Snapshot: if step uses a library template, copy its content into the step
    if first_step.message_template_id and not first_step.template_content:
        tpl = (await db.execute(
            select(MessageTemplate).where(MessageTemplate.id == first_step.message_template_id)
        )).scalar_one_or_none()
        if tpl:
            first_step.template_content = tpl.body
            if tpl.subject and not first_step.subject_template:
                first_step.subject_template = tpl.subject
            tpl.usage_count = (tpl.usage_count or 0) + 1
            tpl.last_used_at = datetime.now(timezone.utc)
            await db.flush()
            logger.info("campaign_execute: SNAPSHOT template=%s into step", str(tpl.id)[:8])

    logger.info("campaign_execute: START | campaign=%s step=%d contacts=%d channel=%s",
        str(campaign_id)[:8], first_step.step_number, len(contacts), first_step.channel.value)

    sent = 0
    failed = 0
    skipped = 0

    for contact in contacts:
        try:
            # Check if contact has the required channel
            if first_step.channel == ChannelType.whatsapp and not contact.phone:
                skipped += 1
                continue
            if first_step.channel == ChannelType.email and not contact.email:
                skipped += 1
                continue

            # Personalize message
            body = personalize_message(
                first_step.template_content or "",
                contact,
                tenant.company_name,
            )

            if not body:
                skipped += 1
                continue

            # Send message
            result = None
            if first_step.channel == ChannelType.whatsapp:
                phone = contact.phone.replace("+", "").replace(" ", "")
                if gupshup_direct.is_configured:
                    result = await gupshup_direct.send_session_message(
                        destination=phone, text=body,
                    )
                else:
                    skipped += 1
                    continue
            else:
                # Email sending via pluggable provider
                email_provider = get_email_provider()
                subject = personalize_message(
                    first_step.subject_template or f"Message from {tenant.company_name}",
                    contact,
                    tenant.company_name,
                )
                from_email = getattr(tenant, "default_from_email", None) or "noreply@tradecrm.io"
                from_name = tenant.company_name or "TradeCRM"
                result = await email_provider.send(
                    to_email=contact.email,
                    from_email=from_email,
                    from_name=from_name,
                    subject=subject,
                    html_body=f"<div>{body}</div>",
                    tracking_id=str(campaign_id),
                )

            # Create message record
            message = Message(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                campaign_step_id=first_step.id,
                contact_id=contact.id,
                channel=first_step.channel,
                direction=MessageDirection.outbound,
                subject=first_step.subject_template if first_step.channel == ChannelType.email else None,
                body=body,
                status=MessageStatus.sent if (result and result.success) else MessageStatus.failed,
                external_id=result.message_id if result else None,
                sent_at=datetime.now(timezone.utc) if (result and result.success) else None,
                failed_reason=result.error if (result and not result.success) else None,
                personalization_data={"contact_name": contact.name, "template": first_step.template_content[:100] if first_step.template_content else None},
            )
            db.add(message)

            if result and result.success:
                sent += 1
                logger.info("campaign_execute: SENT | campaign=%s contact=%s channel=%s",
                    str(campaign_id)[:8], contact.name[:20], first_step.channel.value)
            else:
                failed += 1
                logger.warning("campaign_execute: FAILED | campaign=%s contact=%s error=%s",
                    str(campaign_id)[:8], contact.name[:20], result.error if result else "no result")

        except Exception as e:
            failed += 1
            logger.error("campaign_execute: CRASH | campaign=%s contact=%s error=%s",
                str(campaign_id)[:8], contact.name[:20] if contact.name else str(contact.id)[:8], str(e), exc_info=True)

    await db.commit()

    logger.info("campaign_execute: DONE | campaign=%s sent=%d failed=%d skipped=%d",
        str(campaign_id)[:8], sent, failed, skipped)

    return {"sent": sent, "failed": failed, "skipped": skipped, "total_contacts": len(contacts)}
