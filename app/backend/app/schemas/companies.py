from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    year_established: Optional[int] = None
    number_of_employees: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    annual_trade_value_usd: Optional[float] = None
    registration_number: Optional[str] = None
    commodities: List[str] = []
    target_industries: Optional[List[str]] = None
    preferred_origins: Optional[List[str]] = None
    preferred_incoterms: Optional[str] = None
    preferred_payment_terms: Optional[str] = None
    certifications_required: Optional[List[str]] = None
    destination_ports: Optional[List[str]] = None
    import_volume_annual: Optional[float] = None
    shipment_frequency: Optional[str] = None
    bank_name: Optional[str] = None
    bank_country: Optional[str] = None
    bank_swift_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    tax_id: Optional[str] = None
    rating: Optional[str] = None
    tags: Optional[List[str]] = None
    known_suppliers: Optional[List[str]] = None
    trade_references: Optional[List[Dict[str, str]]] = None
    social_media: Optional[Dict[str, str]] = None
    source: str = "manual"
    notes: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    year_established: Optional[int] = None
    number_of_employees: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    annual_trade_value_usd: Optional[float] = None
    registration_number: Optional[str] = None
    commodities: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    preferred_origins: Optional[List[str]] = None
    preferred_incoterms: Optional[str] = None
    preferred_payment_terms: Optional[str] = None
    certifications_required: Optional[List[str]] = None
    destination_ports: Optional[List[str]] = None
    import_volume_annual: Optional[float] = None
    shipment_frequency: Optional[str] = None
    bank_name: Optional[str] = None
    bank_country: Optional[str] = None
    bank_swift_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    tax_id: Optional[str] = None
    rating: Optional[str] = None
    tags: Optional[List[str]] = None
    known_suppliers: Optional[List[str]] = None
    trade_references: Optional[List[Dict[str, str]]] = None
    social_media: Optional[Dict[str, str]] = None
    notes: Optional[str] = None


class CompanyResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    year_established: Optional[int] = None
    number_of_employees: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    annual_trade_value_usd: Optional[float] = None
    registration_number: Optional[str] = None
    commodities: list = []
    target_industries: Optional[list] = None
    preferred_origins: Optional[list] = None
    preferred_incoterms: Optional[str] = None
    preferred_payment_terms: Optional[str] = None
    certifications_required: Optional[list] = None
    destination_ports: Optional[list] = None
    import_volume_annual: Optional[float] = None
    shipment_frequency: Optional[str] = None
    last_shipment_date: Optional[str] = None
    bank_name: Optional[str] = None
    bank_country: Optional[str] = None
    bank_swift_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    tax_id: Optional[str] = None
    rating: Optional[str] = None
    tags: Optional[list] = None
    known_suppliers: Optional[list] = None
    trade_references: Optional[list] = None
    social_media: Optional[dict] = None
    enrichment_status: str
    source: str
    first_contact_date: Optional[str] = None
    last_interaction_at: Optional[str] = None
    total_inquiries: int = 0
    total_deals_won: int = 0
    total_revenue: Optional[float] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PaginatedCompanies(BaseModel):
    items: List[CompanyResponse]
    total: int
    skip: int
    limit: int
