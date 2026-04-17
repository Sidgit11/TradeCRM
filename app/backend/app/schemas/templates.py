"""Pydantic schemas for Message Templates."""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel: str  # "email" or "whatsapp"
    category: str = "custom"
    subject: Optional[str] = None
    body: str = Field(..., min_length=1)
    description: Optional[str] = None
    ai_generated: bool = False
    ai_prompt: Optional[str] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: str
    tenant_id: str
    created_by: Optional[str] = None
    name: str
    channel: str
    category: str
    subject: Optional[str] = None
    body: str
    body_format: str = "plain"
    variables: list = []
    description: Optional[str] = None
    is_archived: bool = False
    is_default: bool = False
    ai_generated: bool = False
    ai_prompt: Optional[str] = None
    last_used_at: Optional[str] = None
    usage_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TemplateGenerateRequest(BaseModel):
    channel: str  # "email" or "whatsapp"
    category: str = "introduction"
    tone: Optional[str] = None  # "professional", "friendly", "direct", "festive"
    context: str = Field(..., min_length=5, max_length=500)
    variables_hint: List[str] = []


class TemplateRefineRequest(BaseModel):
    current_subject: Optional[str] = None
    current_body: str
    action: str  # "shorter", "longer", "formal", "friendly", "add_cta"
    channel: str = "email"


class TemplateGenerateResponse(BaseModel):
    subject: Optional[str] = None
    body: str
    variables_detected: List[str] = []
