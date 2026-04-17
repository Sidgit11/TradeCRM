"""Pydantic schemas for Product-Port Interests."""
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel


class InterestCreate(BaseModel):
    company_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    variety_id: Optional[uuid.UUID] = None
    grade_id: Optional[uuid.UUID] = None
    destination_port_id: Optional[uuid.UUID] = None
    origin_port_id: Optional[uuid.UUID] = None
    role: str = "buyer"
    notes: Optional[str] = None


class InterestUpdate(BaseModel):
    variety_id: Optional[uuid.UUID] = None
    grade_id: Optional[uuid.UUID] = None
    destination_port_id: Optional[uuid.UUID] = None
    origin_port_id: Optional[uuid.UUID] = None
    role: Optional[str] = None
    notes: Optional[str] = None


class InterestResponse(BaseModel):
    id: str
    tenant_id: str
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    product_id: str
    product_name: Optional[str] = None
    variety_id: Optional[str] = None
    variety_name: Optional[str] = None
    grade_id: Optional[str] = None
    grade_name: Optional[str] = None
    destination_port_id: Optional[str] = None
    destination_port_name: Optional[str] = None
    origin_port_id: Optional[str] = None
    origin_port_name: Optional[str] = None
    role: str
    source: str
    confidence: Optional[float] = None
    confidence_level: Optional[str] = None
    evidence: Optional[dict] = None
    status: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class BulkActionRequest(BaseModel):
    interest_ids: List[uuid.UUID]
