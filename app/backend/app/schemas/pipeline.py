from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class PipelineStageResponse(BaseModel):
    id: str
    name: str
    slug: str
    order: int
    color: str

    class Config:
        from_attributes = True


class OpportunityCreate(BaseModel):
    company_id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    stage_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    source: str = "manual"
    value: Optional[float] = None
    commodity: Optional[str] = None
    quantity_mt: Optional[float] = None
    target_price: Optional[float] = None
    our_price: Optional[float] = None
    competitor_price: Optional[float] = None
    incoterms: Optional[str] = None
    payment_terms: Optional[str] = None
    container_type: Optional[str] = None
    number_of_containers: Optional[int] = None
    target_shipment_date: Optional[str] = None
    packaging_requirements: Optional[str] = None
    quality_specifications: Optional[Dict[str, str]] = None
    expected_close_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    notes: Optional[str] = None


class OpportunityUpdate(BaseModel):
    stage_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    value: Optional[float] = None
    commodity: Optional[str] = None
    quantity_mt: Optional[float] = None
    target_price: Optional[float] = None
    our_price: Optional[float] = None
    competitor_price: Optional[float] = None
    incoterms: Optional[str] = None
    payment_terms: Optional[str] = None
    container_type: Optional[str] = None
    number_of_containers: Optional[int] = None
    target_shipment_date: Optional[str] = None
    shipping_line: Optional[str] = None
    packaging_requirements: Optional[str] = None
    quality_specifications: Optional[Dict[str, str]] = None
    expected_close_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    sample_sent: Optional[bool] = None
    sample_sent_date: Optional[str] = None
    sample_approved: Optional[bool] = None
    sample_feedback: Optional[str] = None
    estimated_value_usd: Optional[float] = None
    probability: Optional[int] = None
    loss_reason: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None


class OpportunityMoveRequest(BaseModel):
    stage_id: uuid.UUID


class OpportunityResponse(BaseModel):
    id: str
    display_id: Optional[str] = None
    tenant_id: str
    title: Optional[str] = None
    company_id: str
    company_name: Optional[str] = None
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    stage_id: str
    stage_name: Optional[str] = None
    stage_color: Optional[str] = None
    source: str
    value: Optional[float] = None
    commodity: Optional[str] = None
    quantity_mt: Optional[float] = None
    target_price: Optional[float] = None
    our_price: Optional[float] = None
    competitor_price: Optional[float] = None
    estimated_value_usd: Optional[float] = None
    incoterms: Optional[str] = None
    payment_terms: Optional[str] = None
    container_type: Optional[str] = None
    number_of_containers: Optional[int] = None
    target_shipment_date: Optional[str] = None
    shipping_line: Optional[str] = None
    packaging_requirements: Optional[str] = None
    quality_specifications: Optional[dict] = None
    expected_close_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    probability: int = 0
    sample_sent: bool = False
    sample_approved: Optional[bool] = None
    sample_feedback: Optional[str] = None
    currency: str = "USD"
    loss_reason: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[list] = None
    is_archived: bool = False
    sample_sent_date: Optional[str] = None
    closed_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PipelineStats(BaseModel):
    total_opportunities: int = 0
    total_value: float = 0
    by_stage: list = []
