"""Canonical template variable registry and resolver."""
import re
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger("services.template_variables")

# Canonical variable registry — single source of truth
TEMPLATE_VARIABLES: Dict[str, Dict[str, str]] = {
    "contact_first_name": {
        "source": "Contact.name first token",
        "example": "Ahmad",
        "fallback": "there",
        "description": "Contact's first name",
    },
    "contact_name": {
        "source": "Contact.name",
        "example": "Ahmad Khan",
        "fallback": "",
        "description": "Contact's full name",
    },
    "contact_title": {
        "source": "Contact.title",
        "example": "Head of Procurement",
        "fallback": "",
        "description": "Contact's job title",
    },
    "contact_salutation": {
        "source": "Contact.salutation + last name",
        "example": "Mr. Khan",
        "fallback": "Dear Sir/Madam",
        "description": "Formal salutation",
    },
    "company_name": {
        "source": "Company.name",
        "example": "Al Noor Trading LLC",
        "fallback": "your company",
        "description": "Buyer's company name",
    },
    "company_country": {
        "source": "Company.country",
        "example": "UAE",
        "fallback": "",
        "description": "Buyer's country",
    },
    "tenant_company": {
        "source": "Tenant.company_name",
        "example": "Kerala Spices Pvt Ltd",
        "fallback": "",
        "description": "Your company name",
    },
    "tenant_sender_name": {
        "source": "User.name",
        "example": "Siddhant",
        "fallback": "",
        "description": "Sender's name",
    },
    "product": {
        "source": "Campaign context / catalog",
        "example": "Black Pepper",
        "fallback": "our products",
        "description": "Product being offered",
    },
    "origin_port": {
        "source": "Tenant default port",
        "example": "Cochin",
        "fallback": "",
        "description": "Shipment origin port",
    },
    "destination_port": {
        "source": "Contact product-port map",
        "example": "Jebel Ali",
        "fallback": "",
        "description": "Shipment destination port",
    },
    "fob_price": {
        "source": "Latest FobPrice for grade",
        "example": "USD 5,200/MT",
        "fallback": "",
        "description": "Current FOB price",
    },
    "payment_terms": {
        "source": "Tenant default or contact preference",
        "example": "30% TT + 70% against BL",
        "fallback": "",
        "description": "Payment terms",
    },
    "season": {
        "source": "Derived from current month",
        "example": "new crop season",
        "fallback": "this season",
        "description": "Current trade season",
    },
}

VAR_PATTERN = re.compile(r"\{\{([a-z_][a-z0-9_.]*)\}\}")


def detect_variables(text: str) -> List[str]:
    """Extract all {{var}} keys from text."""
    if not text:
        return []
    return list(set(VAR_PATTERN.findall(text)))


def get_variable_list() -> List[Dict[str, str]]:
    """Return canonical variable list for frontend consumption."""
    return [
        {"key": key, **info}
        for key, info in TEMPLATE_VARIABLES.items()
    ]


def resolve_variables(
    text: str,
    contact: Optional[Any] = None,
    company: Optional[Any] = None,
    tenant: Optional[Any] = None,
    user: Optional[Any] = None,
    context: Optional[Dict[str, str]] = None,
) -> str:
    """Replace {{var}} placeholders with actual values.

    Lines where all variables resolve to empty are kept but with vars removed.
    """
    if not text:
        return text

    context = context or {}

    def _resolve(key: str) -> str:
        # Context overrides take priority (e.g. campaign-specific product)
        if key in context:
            return context[key]

        meta = TEMPLATE_VARIABLES.get(key, {})
        fallback = meta.get("fallback", "")

        if key == "contact_first_name" and contact:
            name = getattr(contact, "name", None) or ""
            return name.split()[0] if name else fallback
        if key == "contact_name" and contact:
            return getattr(contact, "name", None) or fallback
        if key == "contact_title" and contact:
            return getattr(contact, "title", None) or fallback
        if key == "contact_salutation" and contact:
            sal = getattr(contact, "salutation", None) or ""
            name = getattr(contact, "name", None) or ""
            last = name.split()[-1] if name else ""
            return f"{sal}. {last}".strip(". ") if sal else fallback
        if key == "company_name" and company:
            return getattr(company, "name", None) or fallback
        if key == "company_country" and company:
            return getattr(company, "country", None) or fallback
        if key == "tenant_company" and tenant:
            return getattr(tenant, "company_name", None) or fallback
        if key == "tenant_sender_name" and user:
            return getattr(user, "name", None) or fallback
        if key == "product":
            return fallback
        if key == "season":
            import datetime
            month = datetime.date.today().month
            if month in (10, 11, 12, 1, 2):
                return "new crop season"
            return "current season"

        return fallback

    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        return _resolve(key)

    return VAR_PATTERN.sub(_replacer, text)
