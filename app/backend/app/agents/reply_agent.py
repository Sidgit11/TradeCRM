"""Reply Agent — Trade Communication Assistant.

Classifies inbound messages and suggests appropriate replies.
NEVER auto-sends. NEVER commits to pricing.
"""
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger("agents.reply")

# Keywords for classification
# Ordered by specificity — more specific patterns checked first
CLASSIFICATION_KEYWORDS = [
    ("out_of_office", ["out of office", "ooo", "vacation", "holiday", "auto-reply", "automatic reply"]),
    ("not_interested", ["not interested", "no thanks", "no thank you", "remove me", "don't contact", "stop contacting", "unsubscribe"]),
    ("sample_request", ["send sample", "send us sample", "samples", "sample order", "trial order", "test shipment"]),
    ("meeting_request", ["schedule a call", "meet", "meeting", "zoom call", "visit", "schedule"]),
    ("price_inquiry", ["price", "cost", "rate", "quote", "quotation", "pricing", "how much"]),
    ("interested", ["interested", "tell me more", "send details", "catalogue", "brochure", "want to know more"]),
]


class ReplyAgent:
    """Classifies inbound messages and drafts reply suggestions."""

    TIMEOUT = 30  # seconds

    async def analyze(
        self,
        inbound_text: str,
        contact_name: Optional[str] = None,
        company_name: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        company_data: Optional[Dict] = None,
        tenant_profile: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an inbound message: classify and suggest a reply.

        Returns:
            {
                "classification": str,
                "confidence": float,
                "suggested_reply": str,
                "explanation": str,
            }
        """
        logger.info("Analyzing reply: from=%s text_len=%d", contact_name, len(inbound_text))

        classification = self._classify(inbound_text)
        confidence = self._classification_confidence(inbound_text, classification)

        suggested_reply = self._generate_reply(
            classification=classification,
            inbound_text=inbound_text,
            contact_name=contact_name,
            company_name=company_name,
            tenant_profile=tenant_profile or {},
        )

        explanation = self._explain_classification(classification, inbound_text)

        result = {
            "classification": classification,
            "confidence": confidence,
            "suggested_reply": suggested_reply,
            "explanation": explanation,
        }

        logger.info(
            "Reply analysis: classification=%s confidence=%.2f",
            classification, confidence,
        )
        return result

    def _classify(self, text: str) -> str:
        """Classify the inbound message based on keyword matching (specificity-ordered)."""
        text_lower = text.lower()

        # Check in priority order — most specific first
        for classification, keywords in CLASSIFICATION_KEYWORDS:
            for keyword in keywords:
                if keyword in text_lower:
                    return classification

        # If short reply with positive sentiment
        if len(text.split()) <= 5:
            positive = ["yes", "ok", "sure", "great", "good", "please"]
            if any(word in text_lower for word in positive):
                return "interested"

        return "auto_reply"

    def _classification_confidence(self, text: str, classification: str) -> float:
        """Estimate confidence in the classification."""
        text_lower = text.lower()
        keywords = []
        for cls, kws in CLASSIFICATION_KEYWORDS:
            if cls == classification:
                keywords = kws
                break
        matches = sum(1 for kw in keywords if kw in text_lower)

        if matches >= 2:
            return 0.9
        if matches == 1:
            return 0.75
        return 0.5

    def _generate_reply(
        self,
        classification: str,
        inbound_text: str,
        contact_name: Optional[str],
        company_name: Optional[str],
        tenant_profile: Dict,
    ) -> str:
        """Generate a suggested reply based on classification."""
        name = (contact_name or "").split()[0] if contact_name else "there"
        tenant = tenant_profile.get("company_name", "our team")

        replies = {
            "interested": (
                f"Hi {name}, thank you for your interest! "
                f"I would be happy to share our detailed product catalog and pricing. "
                f"Could you let me know which specific products you are looking for "
                f"and your estimated volume requirements?"
            ),
            "price_inquiry": (
                f"Hi {name}, thank you for reaching out about pricing. "
                f"Our pricing depends on volume, specifications, and delivery terms. "
                f"Could you share your requirements so I can prepare a detailed quotation?"
            ),
            "sample_request": (
                f"Hi {name}, absolutely — we would be glad to arrange samples for you. "
                f"Could you confirm which products and grades you would like to sample, "
                f"along with your shipping address?"
            ),
            "meeting_request": (
                f"Hi {name}, that sounds great. I would be happy to schedule a call. "
                f"What times work best for you this week?"
            ),
            "not_interested": (
                f"Hi {name}, thank you for letting us know. "
                f"We appreciate your time and wish you all the best. "
                f"Should your sourcing needs change in the future, please don't hesitate to reach out."
            ),
            "out_of_office": None,  # Don't reply to OOO
            "auto_reply": (
                f"Hi {name}, thank you for your message. "
                f"I wanted to follow up — is there anything specific I can help with "
                f"regarding your sourcing requirements?"
            ),
        }

        return replies.get(classification, replies["auto_reply"]) or ""

    def _explain_classification(self, classification: str, text: str) -> str:
        """Explain why this classification was chosen."""
        explanations = {
            "interested": "The message expresses interest in learning more about products or services.",
            "price_inquiry": "The message asks about pricing, costs, or quotations.",
            "sample_request": "The message requests product samples or trial orders.",
            "meeting_request": "The message suggests scheduling a meeting or call.",
            "not_interested": "The message indicates the contact is not interested or wants to be removed.",
            "out_of_office": "This appears to be an automated out-of-office response.",
            "auto_reply": "The message could not be clearly classified. It may need manual review.",
        }
        return explanations.get(classification, "Classification based on message content analysis.")


reply_agent = ReplyAgent()
