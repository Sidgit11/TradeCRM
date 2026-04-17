"""Composer Agent — Trade Outreach Specialist.

Generates personalized outreach messages for WhatsApp and Email,
using contact data, company research, and tenant profile.
"""
from typing import Any, Dict, Optional

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("agents.composer")


class ComposerAgent:
    """Composes personalized outreach messages using trade intelligence."""

    TIMEOUT = 30  # seconds

    async def compose(
        self,
        contact_name: str,
        contact_title: Optional[str],
        company_name: Optional[str],
        company_data: Optional[Dict[str, Any]],
        channel: str,  # "whatsapp" or "email"
        campaign_context: Optional[str],
        tenant_profile: Dict[str, Any],
        past_messages: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Generate a personalized outreach message.

        Returns:
            {
                "subject": str (email only),
                "body": str,
                "personalization_explanation": str,
                "variables_used": dict,
            }
        """
        logger.info(
            "Composing message: contact=%s company=%s channel=%s",
            contact_name, company_name, channel,
        )

        # Build context for personalization
        tenant_name = tenant_profile.get("company_name", "our company")
        tenant_commodities = tenant_profile.get("commodities", [])
        commodity_str = ", ".join(tenant_commodities[:3]) if tenant_commodities else "quality products"

        # Extract company intelligence if available
        buyer_commodities = []
        buyer_volume = None
        if company_data:
            buyer_commodities = company_data.get("commodities", [])
            buyer_volume = company_data.get("import_volume_annual")

        # Build personalization variables
        variables = {
            "contact_name": contact_name,
            "contact_title": contact_title or "",
            "company_name": company_name or "",
            "tenant_name": tenant_name,
            "commodities": commodity_str,
            "buyer_commodities": ", ".join(buyer_commodities[:3]) if buyer_commodities else "",
        }

        explanation_parts = [f"Addressed to {contact_name}"]
        if company_name:
            explanation_parts.append(f"at {company_name}")
        if buyer_commodities:
            explanation_parts.append(f"who imports {', '.join(buyer_commodities[:2])}")

        if channel == "whatsapp":
            body = self._compose_whatsapp(variables, campaign_context)
        else:
            body = self._compose_email_body(variables, campaign_context)

        subject = None
        if channel == "email":
            subject = self._compose_email_subject(variables, campaign_context)

        result = {
            "subject": subject,
            "body": body,
            "personalization_explanation": ". ".join(explanation_parts) + ".",
            "variables_used": variables,
        }

        logger.info("Message composed: channel=%s len=%d", channel, len(body))
        return result

    def _compose_whatsapp(self, variables: Dict, context: Optional[str]) -> str:
        """Compose a concise WhatsApp message."""
        name = variables["contact_name"].split()[0]  # first name only
        tenant = variables["tenant_name"]
        commodities = variables["commodities"]

        if context and "follow" in context.lower():
            return (
                f"Hi {name}, following up on my earlier message. "
                f"We at {tenant} have fresh stock of {commodities} available. "
                f"Would you be open to discussing quantities and pricing?"
            )

        return (
            f"Hi {name}, I'm reaching out from {tenant}. "
            f"We are exporters of premium {commodities}. "
            f"I noticed your company's sourcing activity and wanted to explore "
            f"if there's a fit. Happy to share samples and pricing."
        )

    def _compose_email_body(self, variables: Dict, context: Optional[str]) -> str:
        """Compose a professional email body."""
        name = variables["contact_name"]
        company = variables["company_name"]
        tenant = variables["tenant_name"]
        commodities = variables["commodities"]
        buyer_comms = variables.get("buyer_commodities", "")

        greeting = f"Dear {name},"
        if variables.get("contact_title"):
            greeting = f"Dear {variables['contact_title']} {name.split()[-1]},"

        intro = f"I am writing from {tenant}, a leading exporter of {commodities}."

        if buyer_comms:
            bridge = (
                f"Based on our research, {company} has been actively importing "
                f"{buyer_comms}, and we believe our product quality and pricing "
                f"would be a strong fit for your requirements."
            )
        elif company:
            bridge = (
                f"We came across {company} and believe there could be a strong "
                f"opportunity for collaboration."
            )
        else:
            bridge = "We are expanding our buyer network and would welcome the opportunity to connect."

        cta = (
            "We would be glad to share detailed product specifications, pricing, "
            "and arrange samples at your convenience."
        )

        close = f"Looking forward to hearing from you.\n\nBest regards,\n{tenant}"

        return f"{greeting}\n\n{intro}\n\n{bridge}\n\n{cta}\n\n{close}"

    def _compose_email_subject(self, variables: Dict, context: Optional[str]) -> str:
        """Compose an email subject line."""
        tenant = variables["tenant_name"]
        commodities = variables["commodities"]

        if context and "follow" in context.lower():
            return f"Following up — {commodities} from {tenant}"

        return f"Premium {commodities} — Introduction from {tenant}"


composer_agent = ComposerAgent()
