"""Reply Drafter — generates contextual reply drafts for inbound leads using Gemini."""
import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging_config import get_logger
from app.utils.gemini import safe_parse_json, GEMINI_URL

logger = get_logger("agents.reply_drafter")

_REPLY_FALLBACK = {"subject": "", "body": "", "explanation": ""}


def _parse_gemini_json(text: str) -> dict:
    """Parse Gemini reply JSON, with regex fallback for reply-specific fields."""
    parsed = safe_parse_json(text, fallback=None)
    if parsed:
        return parsed

    # Regex fallback specific to reply fields
    subject = ""
    body = ""
    explanation = ""

    subj_match = re.search(r'"subject"\s*:\s*"([^"]*)"', text)
    if subj_match:
        subject = subj_match.group(1)

    body_match = re.search(r'"body"\s*:\s*"(.*?)"\s*[,}]', text, re.DOTALL)
    if body_match:
        body = body_match.group(1).replace("\\n", "\n").replace('\\"', '"')
    else:
        body = text

    expl_match = re.search(r'"explanation"\s*:\s*"(.*?)"', text, re.DOTALL)
    if expl_match:
        explanation = expl_match.group(1)

    logger.info("Parsed Gemini JSON via regex fallback")
    return {"subject": subject, "body": body, "explanation": explanation}


async def draft_reply(
    lead_data: Dict[str, Any],
    tenant_profile: Dict[str, Any],
    catalog_context: str,
    pricing_context: str,
    preferences: Optional[Dict[str, Any]] = None,
    user_instruction: str = "",
    channel: str = "email",
) -> Dict[str, str]:
    """Generate a reply draft for an inbound lead using Gemini. Channel: email or whatsapp."""

    sender = lead_data.get("sender_email", "unknown")
    logger.info("draft_reply: START | to=%s channel=%s instruction='%s'", sender[:40], channel, user_instruction[:50])

    if not settings.GOOGLE_API_KEY:
        logger.warning("draft_reply: no GOOGLE_API_KEY, returning mock | to=%s", sender[:40])
        return {"draft": "Thank you for your inquiry. We will get back to you shortly.", "explanation": "Mock reply (no API key)"}

    prefs = preferences or {}
    tone = prefs.get("reply_tone", "formal")
    language = prefs.get("reply_language", "match_sender")
    include_fob = prefs.get("include_fob_price", True)
    include_cfr = prefs.get("include_cfr_quote", True)
    include_certs = prefs.get("include_certifications", True)
    include_moq = prefs.get("include_moq", True)
    high_value_style = prefs.get("high_value_reply_style", "")
    custom_instructions = prefs.get("custom_reply_instructions", "")

    is_high_value = lead_data.get("is_high_value", False)

    prompt = f"""You are a trade communication assistant for {tenant_profile.get('company_name', 'our company')},
an exporter of {', '.join(tenant_profile.get('commodities', []))}.

SENDER:
- Name: {lead_data.get('sender_name', 'Unknown')}
- Company: {lead_data.get('sender_company', 'Unknown')}
- Designation: {lead_data.get('sender_designation', '')}

THEIR INQUIRY:
- Subject: {lead_data.get('subject', '')}
- Products wanted: {json.dumps(lead_data.get('products_mentioned', []))}
- Quantities: {json.dumps(lead_data.get('quantities', []))}
- Delivery terms: {lead_data.get('delivery_terms', 'not specified')}
- Destination: {lead_data.get('destination', 'not specified')}
- Urgency: {lead_data.get('urgency', 'not specified')}
- Specific questions: {lead_data.get('specific_questions', 'none')}
- Their email: {lead_data.get('body_preview', '')[:1000]}

OUR CATALOG & PRICING:
{catalog_context}

{pricing_context}

REPLY RULES:
- Tone: {tone}
- Language: {"Match the sender's language" if language == "match_sender" else "English"}
{"- Include current FOB price" if include_fob else "- Do NOT mention prices"}
{"- Include CFR estimate if destination is known" if include_cfr else ""}
{"- Mention our certifications" if include_certs else ""}
{"- Mention minimum order quantity" if include_moq else ""}
{"- HIGH VALUE INQUIRY: " + high_value_style if is_high_value and high_value_style else ""}
{("- Additional instructions: " + custom_instructions) if custom_instructions else ""}

USER'S INTENT FOR THIS REPLY:
{user_instruction if user_instruction else "Reply professionally to their inquiry based on available information."}

CHANNEL: {"WhatsApp" if channel == "whatsapp" else "Email"}
{"WHATSAPP RULES:" if channel == "whatsapp" else "EMAIL RULES:"}
{'''- Keep it SHORT — max 3-4 lines
- No formal salutations like "Dear Mr." — use first name or "Hi"
- No email-style sign-offs
- Conversational but professional
- Use line breaks, not paragraphs
- Include key info: product, price range, availability''' if channel == "whatsapp" else '''- Professional email format with proper greeting and sign-off
- Address the buyer's specific questions
- Keep it concise but thorough'''}

CRITICAL RULES:
- NEVER commit to a final price — use "indicative" or "current" language
- NEVER make promises about delivery dates without checking
- Be professional and helpful

Generate a reply. Respond with JSON only:
{{
  "subject": "{"" if channel == "whatsapp" else "Re: ..."}",
  "body": "the full reply text",
  "explanation": "brief explanation of why this reply was drafted this way"
}}"""

    logger.debug("draft_reply: prompt_len=%d", len(prompt))

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{GEMINI_URL}?key={settings.GOOGLE_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
                },
            )

            if response.status_code != 200:
                logger.error("draft_reply: Gemini API error %d | to=%s | body=%s", response.status_code, sender[:40], response.text[:200])
                return {"draft": "", "explanation": f"API error: {response.status_code}"}

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.error("draft_reply: no candidates returned | to=%s", sender[:40])
                return {"draft": "", "explanation": "No response from AI"}

            parts = candidates[0].get("content", {}).get("parts", [])
            finish_reason = candidates[0].get("finishReason", "unknown")
            logger.info("draft_reply: Gemini responded | parts=%d finish=%s thinking=%d | to=%s",
                len(parts), finish_reason, sum(1 for p in parts if p.get("thought")), sender[:40])

            if finish_reason == "MAX_TOKENS":
                logger.warning("draft_reply: output truncated by MAX_TOKENS | to=%s", sender[:40])

            text = ""
            for part in parts:
                if "text" in part and not part.get("thought"):
                    text = part["text"]
            if not text:
                text = parts[-1].get("text", "") if parts else ""
                logger.warning("draft_reply: no non-thinking part, using fallback | to=%s", sender[:40])

            text = text.strip()
            text = re.sub(r"^```json?\s*\n?", "", text)
            text = re.sub(r"\n?\s*```\s*$", "", text)
            text = text.strip()

            result = _parse_gemini_json(text)
            draft_body = result.get("body", "")

            logger.info("draft_reply: DONE | to=%s channel=%s draft_len=%d subject=%s",
                sender[:40], channel, len(draft_body), result.get("subject", "")[:50])
            return {
                "subject": result.get("subject", ""),
                "draft": draft_body,
                "explanation": result.get("explanation", ""),
            }

    except httpx.TimeoutException:
        logger.error("draft_reply: TIMEOUT | to=%s channel=%s", sender[:40], channel)
        return {"draft": "", "explanation": "AI request timed out. Try again."}
    except Exception as e:
        logger.error("draft_reply: ERROR | to=%s type=%s error=%s", sender[:40], type(e).__name__, str(e))
        return {"draft": "", "explanation": f"Error: {str(e)}"}
