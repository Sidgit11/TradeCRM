from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    salutation: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    secondary_email: Optional[str] = None
    phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    department: Optional[str] = None
    is_decision_maker: bool = False
    preferred_language: Optional[str] = None
    preferred_channel: Optional[str] = None
    do_not_contact: bool = False
    linkedin_url: Optional[str] = None
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}
    opted_in_whatsapp: bool = False
    opted_in_email: bool = True
    source: str = "manual"
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    salutation: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    secondary_email: Optional[str] = None
    phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    department: Optional[str] = None
    is_decision_maker: Optional[bool] = None
    preferred_language: Optional[str] = None
    preferred_channel: Optional[str] = None
    do_not_contact: Optional[bool] = None
    linkedin_url: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    opted_in_whatsapp: Optional[bool] = None
    opted_in_email: Optional[bool] = None
    notes: Optional[str] = None


class ContactResponse(BaseModel):
    id: str
    tenant_id: str
    salutation: Optional[str] = None
    name: str
    email: Optional[str] = None
    secondary_email: Optional[str] = None
    phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    is_decision_maker: bool = False
    preferred_language: Optional[str] = None
    preferred_channel: Optional[str] = None
    do_not_contact: bool = False
    linkedin_url: Optional[str] = None
    tags: list = []
    custom_fields: dict = {}
    opted_in_whatsapp: bool
    opted_in_email: bool
    enrichment_status: str
    source: str
    total_interactions: int = 0
    first_seen_at: Optional[str] = None
    last_interaction_at: Optional[str] = None
    last_contacted_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ContactListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ContactListResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    member_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class PaginatedContacts(BaseModel):
    items: List[ContactResponse]
    total: int
    skip: int
    limit: int
