"""Template Author Agent — generates reusable message templates with AI."""
import httpx
from typing import Dict, List, Optional

from app.config import settings
from app.logging_config import get_logger
from app.utils.gemini import safe_parse_json, GEMINI_URL, extract_gemini_text
from app.services.template_variables import TEMPLATE_VARIABLES, detect_variables

logger = get_logger("agents.template_author")

VARIABLE_KEYS = ", ".join(f"{{{{{k}}}}}" for k in TEMPLATE_VARIABLES.keys())


def _system_prompt(channel: str, category: str, tone: Optional[str]) -> str:
    tone_rules = {
        "professional": "Use formal language. No contractions. Address as Mr./Ms. Use complete sentences.",
        "friendly": "Use first name, casual opener. Warm and approachable. Contractions okay.",
        "direct": "Extremely concise. 2-3 sentences max for body. No filler words.",
        "festive": "Warm, celebratory tone. Can use exclamation marks. Reference the season/festival.",
    }
    tone_instruction = tone_rules.get(tone or "professional", tone_rules["professional"])

    channel_rules = ""
    if channel == "whatsapp":
        channel_rules = """
WhatsApp rules:
- Body must be 300 characters or less
- Do NOT generate a subject line
- Keep it conversational and brief
- One clear CTA at the end"""
    else:
        channel_rules = """
Email rules:
- Subject line: 5-9 words, compelling, no spam words
- Body: 80-160 words for introduction, 40-80 for price update/follow-up
- Include a clear CTA
- Professional email structure: greeting, body, CTA, sign-off"""

    return f"""You are a template author for commodity trade outreach messages.
You create reusable message templates with variable placeholders.

CRITICAL RULES:
1. Use ONLY these variables (double curly braces): {VARIABLE_KEYS}
2. NEVER hardcode names, prices, company names, or products — always use variables
3. Always include at least one CTA (call to action)
4. Templates should sound human, not robotic

{channel_rules}

Tone: {tone_instruction}

Category "{category}" context:
- introduction: First contact with a potential buyer. Introduce the exporter and key products.
- price_update: Share current pricing to existing contacts. Reference product and FOB/CIF price.
- follow_up: Follow up on a previous conversation or unanswered message.
- sample_offer: Offer product samples to interested buyers.
- order_confirmation: Confirm an order with details.
- festive_greeting: Holiday/seasonal greeting with soft sell.
- reactivation: Re-engage dormant contacts.
- custom: General purpose based on user's context.

Return ONLY valid JSON with keys: "subject" (null for whatsapp), "body"."""


async def generate(
    channel: str,
    category: str,
    tone: Optional[str],
    context: str,
    variables_hint: List[str],
    tenant_name: Optional[str] = None,
    tenant_commodities: Optional[List[str]] = None,
) -> Dict:
    """Generate a template using AI."""
    system = _system_prompt(channel, category, tone)

    hint_str = ""
    if variables_hint:
        hint_str = f"\nVariables to include: {', '.join('{{' + v + '}}' for v in variables_hint)}"

    tenant_ctx = ""
    if tenant_name:
        tenant_ctx = f"\nThe exporter company is: {tenant_name}"
        if tenant_commodities:
            tenant_ctx += f", dealing in: {', '.join(tenant_commodities[:5])}"

    user_prompt = f"""Generate a {channel} template for category "{category}".

User's context: {context}{hint_str}{tenant_ctx}

Return JSON: {{"subject": "..." or null, "body": "..."}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1024},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        raw = extract_gemini_text(parts)
        parsed = safe_parse_json(raw, fallback={"subject": None, "body": context})

        subject = parsed.get("subject")
        body = parsed.get("body", context)

        # Detect variables in generated content
        all_text = f"{subject or ''} {body}"
        vars_detected = detect_variables(all_text)

        logger.info("template_generate: channel=%s category=%s vars=%d", channel, category, len(vars_detected))
        return {"subject": subject, "body": body, "variables_detected": vars_detected}

    except Exception as e:
        logger.error("template_generate failed: %s", str(e), exc_info=True)
        return {"subject": None, "body": context, "variables_detected": []}


async def refine(
    current_body: str,
    current_subject: Optional[str],
    action: str,
    channel: str,
) -> Dict:
    """Refine an existing template (shorter, longer, formal, friendly, add_cta)."""
    action_prompts = {
        "shorter": "Make this message significantly shorter. Cut any filler. Keep the core message and CTA.",
        "longer": "Expand this message with more detail. Add context about the product/company. Keep it professional.",
        "formal": "Make this more formal and professional. Remove any casual language. Use proper business English.",
        "friendly": "Make this warmer and more friendly. Use first name, add a personal touch. Keep it professional but approachable.",
        "add_cta": "Add a clear, compelling call-to-action at the end. Examples: schedule a call, request samples, share catalog.",
    }

    prompt = action_prompts.get(action, f"Refine this message: {action}")

    channel_note = ""
    if channel == "whatsapp":
        channel_note = "\nKeep body under 300 characters. No subject needed."
    else:
        channel_note = "\nKeep subject 5-9 words. Body 60-180 words."

    user_prompt = f"""{prompt}{channel_note}

Current subject: {current_subject or '(none)'}
Current body:
{current_body}

Return JSON: {{"subject": "..." or null, "body": "..."}}
Keep all {{{{variable}}}} placeholders intact."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
                json={
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        raw = extract_gemini_text(parts)
        parsed = safe_parse_json(raw, fallback={"subject": current_subject, "body": current_body})

        return {"subject": parsed.get("subject"), "body": parsed.get("body", current_body)}

    except Exception as e:
        logger.error("template_refine failed: %s", str(e), exc_info=True)
        return {"subject": current_subject, "body": current_body}
