"""Lead Classification Agent — uses Gemini to classify emails and extract lead data."""
import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging_config import get_logger
from app.utils.gemini import safe_parse_json, GEMINI_URL

logger = get_logger("agents.lead_classifier")

_CLASSIFY_FALLBACK = {"classification": "non_lead", "confidence": 0.3, "non_lead_reason": "other"}


def _safe_parse_json(text: str) -> dict:
    return safe_parse_json(text, fallback=_CLASSIFY_FALLBACK)

# Patterns to skip before even calling LLM
SKIP_PATTERNS = {
    "senders": [
        "noreply@", "no-reply@", "mailer-daemon@", "notifications@",
        "alerts@", "donotreply@", "do-not-reply@", "updates@",
        "marketing@", "newsletter@", "promo@", "promotions@",
        "jobalerts@", "jobalerts-noreply@",
    ],
    "sender_domains": [
        "linkedin.com", "facebook.com", "twitter.com", "instagram.com",
        "youtube.com", "google.com", "swiggy.in", "zomato.com",
        "myntra.com", "flipkart.com", "amazon.in", "amazon.com",
        "paytm.com", "phonepe.com", "gpay.com",
        "axisbank", "hdfcbank", "icicibank", "sbibank",
        "substack.com", "medium.com",
    ],
    "subjects": [
        "otp", "verify your", "password reset", "two-factor", "2fa",
        "unsubscribe", "order delivered", "order confirmed",
        "payment received", "transaction alert", "credit card",
    ],
}


def should_skip_email(from_addr: str, subject: str, headers: Dict[str, str] = {}) -> Optional[str]:
    """Quick filter — skip obvious non-business emails without calling LLM."""
    from_lower = from_addr.lower()
    subj_lower = subject.lower()

    for pattern in SKIP_PATTERNS["senders"]:
        if pattern in from_lower:
            return "notification"

    for pattern in SKIP_PATTERNS.get("sender_domains", []):
        if pattern in from_lower:
            return "notification"

    for pattern in SKIP_PATTERNS["subjects"]:
        if pattern in subj_lower:
            return "notification"

    if "list-unsubscribe" in headers.get("list-unsubscribe", "").lower() or "list-unsubscribe" in str(headers):
        return "newsletter"

    # Check for unsubscribe link in body (common in marketing emails)
    # This is checked in the processor, not here (we don't have body yet)
    return None


def _build_classification_prompt(
    email_from: str,
    subject: str,
    body: str,
    tenant_name: str,
    tenant_commodities: List[str],
    catalog_products: List[Dict[str, Any]],
    preferences: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the Gemini prompt for classification + extraction."""
    # Build catalog summary
    catalog_lines = []
    for p in catalog_products[:30]:  # limit to 30 products
        varieties = ", ".join([v.get("name", "") for v in p.get("varieties", [])])
        aliases = ", ".join(p.get("aliases", [])[:5]) if p.get("aliases") else ""
        line = f"- {p['name']} (origin: {p.get('origin_country', '?')})"
        if varieties:
            line += f" | varieties: {varieties}"
        if aliases:
            line += f" | aliases: {aliases}"
        catalog_lines.append(line)

    catalog_text = "\n".join(catalog_lines) if catalog_lines else "No products in catalog yet."

    # Preference rules
    pref_rules = []
    if preferences:
        if preferences.get("ignore_below_qty_mt"):
            pref_rules.append(f"- Mark as non_lead if quantity mentioned is below {preferences['ignore_below_qty_mt']} MT")
        if preferences.get("ignore_countries"):
            countries = ", ".join(preferences["ignore_countries"])
            pref_rules.append(f"- Mark as non_lead if sender is from: {countries}")
        if preferences.get("auto_non_lead_if_no_catalog_match", True):
            pref_rules.append("- If the product they want is clearly not in the catalog, mark as non_lead with reason 'product_not_in_catalog'")

    pref_text = "\n".join(pref_rules) if pref_rules else "No special rules."

    return f"""You are a trade email classifier for {tenant_name}, an exporter of {', '.join(tenant_commodities)}.

CATALOG PRODUCTS:
{catalog_text}

CLASSIFICATION RULES:
{pref_text}

TASK:
Analyze this email. Determine if it's a genuine buying/trade inquiry (lead) or not (non_lead).
Extract structured data from the email body and signature.

EMAIL:
From: {email_from}
Subject: {subject}
Body:
{body[:3000]}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "classification": "lead" or "non_lead",
  "non_lead_reason": null or "newsletter" or "notification" or "job_application" or "vendor_pitch" or "personal" or "below_min_qty" or "blocked_country" or "product_not_in_catalog" or "spam" or "other",
  "confidence": 0.0 to 1.0,
  "sender_name": "extracted full name" or null,
  "sender_phone": "extracted phone with country code" or null,
  "sender_company": "extracted company name" or null,
  "sender_designation": "extracted job title" or null,
  "sender_department": "Purchasing/Trading/Management/other" or null,
  "is_decision_maker": true or false,
  "company_type": "importer/distributor/manufacturer/broker/retailer/agent" or null,
  "company_country": "country of the sender's company" or null,
  "company_city": "city if mentioned" or null,
  "products_mentioned": ["exact product text as mentioned in email"],
  "quantities": [{{"raw": "20 MT", "value": 20, "unit": "MT"}}] or [],
  "target_price": "mentioned price" or null,
  "delivery_terms": "FOB" or "CIF" or "CFR" or "CnF" or null,
  "payment_terms": "LC at sight/TT advance/CAD/DA" or null,
  "destination": "country or port mentioned" or null,
  "certifications_mentioned": ["Organic", "Fair Trade"] or [],
  "urgency": "immediate" or "this_month" or "exploring" or null,
  "specific_questions": "brief summary of what they asked, comma separated" or null,
  "language": "en" or "hi" or detected language code
}}"""


async def classify_email(
    email_from: str,
    subject: str,
    body: str,
    tenant_name: str,
    tenant_commodities: List[str],
    catalog_products: List[Dict[str, Any]],
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Classify an email using Gemini Flash. Returns structured extraction."""

    if not settings.GOOGLE_API_KEY:
        logger.warning("classify_email: GOOGLE_API_KEY not set, returning mock | from=%s subject=%s", email_from[:40], subject[:40])
        return {
            "classification": "lead", "confidence": 0.5,
            "sender_name": email_from.split("<")[0].strip().strip('"'),
            "products_mentioned": [], "quantities": [], "language": "en", "_mock": True,
        }

    logger.info("classify_email: calling Gemini | from=%s subject=%s body_len=%d catalog_count=%d",
        email_from[:50], subject[:50], len(body), len(catalog_products))

    prompt = _build_classification_prompt(
        email_from, subject, body, tenant_name, tenant_commodities, catalog_products, preferences,
    )
    logger.debug("classify_email: prompt_len=%d", len(prompt))

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{GEMINI_URL}?key={settings.GOOGLE_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
                },
            )

            if response.status_code != 200:
                logger.error("classify_email: Gemini API returned %d | from=%s | error=%s",
                    response.status_code, email_from[:40], response.text[:300])
                return {"classification": "lead", "confidence": 0.3, "_error": response.text[:200]}

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.error("classify_email: Gemini returned no candidates | from=%s", email_from[:40])
                return {"classification": "lead", "confidence": 0.3, "_error": "no_candidates"}

            parts = candidates[0].get("content", {}).get("parts", [])
            logger.debug("classify_email: Gemini returned %d parts | thinking_parts=%d",
                len(parts), sum(1 for p in parts if p.get("thought")))

            # Find the text part (skip thinking parts)
            text = ""
            for part in parts:
                if "text" in part and not part.get("thought"):
                    text = part["text"]
            if not text:
                text = parts[-1].get("text", "") if parts else ""
                logger.warning("classify_email: no non-thinking text part, using fallback | parts=%d", len(parts))

            # Clean markdown wrapping
            text = text.strip()
            text = re.sub(r"^```json?\s*\n?", "", text)
            text = re.sub(r"\n?\s*```\s*$", "", text)
            text = text.strip()

            finish_reason = candidates[0].get("finishReason", "unknown")
            logger.info("classify_email: raw_text_len=%d finish_reason=%s | from=%s",
                len(text), finish_reason, email_from[:40])

            if finish_reason == "MAX_TOKENS":
                logger.warning("classify_email: output truncated by MAX_TOKENS! Increase maxOutputTokens | from=%s", email_from[:40])

            result = _safe_parse_json(text)

            logger.info(
                "classify_email: done | from=%s classification=%s confidence=%.2f products=%s phone=%s company=%s",
                email_from[:40], result.get("classification"), result.get("confidence", 0),
                result.get("products_mentioned"), result.get("sender_phone"), result.get("sender_company"),
            )
            return result

    except httpx.TimeoutException:
        logger.error("classify_email: Gemini request timed out | from=%s subject=%s", email_from[:40], subject[:40])
        return {"classification": "lead", "confidence": 0.3, "_error": "timeout"}
    except json.JSONDecodeError as e:
        logger.error("classify_email: JSON decode error | from=%s error=%s", email_from[:40], str(e))
        return {"classification": "lead", "confidence": 0.3, "_error": "invalid_json"}
    except Exception as e:
        logger.error("classify_email: unexpected error | from=%s error=%s type=%s", email_from[:40], str(e), type(e).__name__)
        return {"classification": "lead", "confidence": 0.3, "_error": str(e)}


def match_products_to_catalog(
    products_mentioned: List[str],
    catalog_products: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Match extracted product mentions to the user's catalog. Fuzzy + alias matching."""
    matches = []

    for raw_mention in products_mentioned:
        mention_lower = raw_mention.lower().strip()
        best_match = None
        best_confidence = 0.0

        for product in catalog_products:
            product_name_lower = product["name"].lower()

            # Exact product name match
            if product_name_lower in mention_lower or mention_lower in product_name_lower:
                conf = 0.9
                grade_match = _match_grade(mention_lower, product)
                if grade_match:
                    conf = 0.95
                if conf > best_confidence:
                    best_match = {
                        "raw": raw_mention,
                        "matched_product_id": product["id"],
                        "matched_product_name": product["name"],
                        "matched_grade_id": grade_match.get("id") if grade_match else None,
                        "matched_grade_name": grade_match.get("name") if grade_match else None,
                        "confidence": conf,
                    }
                    best_confidence = conf
                continue

            # Alias match
            for alias in (product.get("aliases") or []):
                if alias.lower() in mention_lower or mention_lower in alias.lower():
                    conf = 0.8
                    grade_match = _match_grade(mention_lower, product)
                    if grade_match:
                        conf = 0.85
                    if conf > best_confidence:
                        best_match = {
                            "raw": raw_mention,
                            "matched_product_id": product["id"],
                            "matched_product_name": product["name"],
                            "matched_grade_id": grade_match.get("id") if grade_match else None,
                            "matched_grade_name": grade_match.get("name") if grade_match else None,
                            "confidence": conf,
                        }
                        best_confidence = conf

        if best_match:
            matches.append(best_match)
        else:
            matches.append({"raw": raw_mention, "matched_product_id": None, "confidence": 0.0})

    return matches


def _match_grade(mention: str, product: Dict) -> Optional[Dict]:
    """Try to match a grade name within the mention text."""
    for variety in product.get("varieties", []):
        for grade in variety.get("grades", []):
            if grade["name"].lower() in mention:
                return {"id": grade["id"], "name": grade["name"], "variety": variety["name"]}
    return None


def match_to_existing_contacts(
    sender_email: str,
    sender_name: Optional[str],
    sender_company: Optional[str],
    existing_contacts: List[Dict[str, Any]],
    existing_companies: List[Dict[str, Any]],
    sender_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """Match sender to existing CRM contacts and companies by email, phone, name, company."""
    result: Dict[str, Any] = {
        "matched_contact_id": None, "matched_contact_confidence": None,
        "matched_company_id": None, "matched_company_confidence": None,
    }

    email_lower = sender_email.lower()

    # Match by email (highest confidence)
    for contact in existing_contacts:
        if contact.get("email", "").lower() == email_lower:
            result["matched_contact_id"] = contact["id"]
            result["matched_contact_confidence"] = 0.99
            if contact.get("company_id"):
                result["matched_company_id"] = contact["company_id"]
                result["matched_company_confidence"] = 0.95
            logger.debug("CRM match by email: %s → contact=%s", email_lower, contact["id"])
            return result

    # Match by phone (high confidence)
    if sender_phone:
        phone_digits = "".join(c for c in sender_phone if c.isdigit())
        if len(phone_digits) >= 10:
            # Match last 10 digits (ignore country code differences)
            phone_suffix = phone_digits[-10:]
            for contact in existing_contacts:
                contact_phone = contact.get("phone", "") or ""
                contact_digits = "".join(c for c in contact_phone if c.isdigit())
                if contact_digits and contact_digits[-10:] == phone_suffix:
                    result["matched_contact_id"] = contact["id"]
                    result["matched_contact_confidence"] = 0.95
                    if contact.get("company_id"):
                        result["matched_company_id"] = contact["company_id"]
                        result["matched_company_confidence"] = 0.90
                    logger.debug("CRM match by phone: %s → contact=%s", sender_phone, contact["id"])
                    return result

    # Match company by name
    if sender_company:
        company_lower = sender_company.lower()
        for company in existing_companies:
            if company["name"].lower() == company_lower:
                result["matched_company_id"] = company["id"]
                result["matched_company_confidence"] = 0.9
                break
            elif company_lower in company["name"].lower() or company["name"].lower() in company_lower:
                result["matched_company_id"] = company["id"]
                result["matched_company_confidence"] = 0.7

    # Match contact by name (lower confidence)
    if sender_name and not result["matched_contact_id"]:
        name_lower = sender_name.lower()
        for contact in existing_contacts:
            if contact.get("name", "").lower() == name_lower:
                result["matched_contact_id"] = contact["id"]
                result["matched_contact_confidence"] = 0.7
                break

    return result
