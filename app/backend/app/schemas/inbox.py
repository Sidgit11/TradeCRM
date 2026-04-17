from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ConversationSummary(BaseModel):
    contact_id: str
    contact_name: str
    company_name: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_at: Optional[str] = None
    channel: str  # whatsapp | email | multi
    unread_count: int = 0
    classification: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    channel: str
    direction: str
    subject: Optional[str] = None
    body: str
    status: str
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    opened_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class ReplyRequest(BaseModel):
    channel: str  # whatsapp | email
    body: str
    subject: Optional[str] = None  # email only


class SuggestionResponse(BaseModel):
    id: str
    message_id: str
    classification: str
    suggested_reply_text: str
    explanation: Optional[str] = None
    confidence: float
    status: str
    created_at: str

    class Config:
        from_attributes = True


class SnoozeRequest(BaseModel):
    hours: int = 4
