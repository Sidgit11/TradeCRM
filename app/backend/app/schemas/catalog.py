from typing import Any, Dict, List, Optional
import uuid
from datetime import date

from pydantic import BaseModel, Field


# --- Ports ---

class PortResponse(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    city: Optional[str] = None
    country: str

    class Config:
        from_attributes = True


# --- Products ---

class GradeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    specifications: Optional[Dict[str, Any]] = None
    packaging_type: Optional[str] = None
    packaging_weight_kg: Optional[float] = None
    moq_mt: Optional[float] = None


class GradeResponse(BaseModel):
    id: str
    name: str
    specifications: Optional[dict] = None
    packaging_type: Optional[str] = None
    packaging_weight_kg: Optional[float] = None
    moq_mt: Optional[float] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class VarietyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    grades: List[GradeCreate] = []


class VarietyResponse(BaseModel):
    id: str
    name: str
    is_active: bool = True
    grades: List[GradeResponse] = []

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    origin_country: str = Field(..., min_length=1, max_length=100)
    hs_code: Optional[str] = None
    description: Optional[str] = None
    default_loading_port_id: Optional[uuid.UUID] = None
    shelf_life_days: Optional[int] = None
    certifications: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    capacity_20ft_mt: Optional[float] = None
    capacity_40ft_mt: Optional[float] = None
    capacity_40ft_hc_mt: Optional[float] = None
    varieties: List[VarietyCreate] = []


class ProductResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    origin_country: str
    hs_code: Optional[str] = None
    description: Optional[str] = None
    default_loading_port_id: Optional[str] = None
    shelf_life_days: Optional[int] = None
    certifications: Optional[list] = None
    aliases: Optional[list] = None
    capacity_20ft_mt: Optional[float] = None
    capacity_40ft_mt: Optional[float] = None
    capacity_40ft_hc_mt: Optional[float] = None
    is_active: bool = True
    varieties: List[VarietyResponse] = []
    created_at: str

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    origin_country: Optional[str] = None
    hs_code: Optional[str] = None
    description: Optional[str] = None
    default_loading_port_id: Optional[uuid.UUID] = None
    shelf_life_days: Optional[int] = None
    certifications: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    capacity_20ft_mt: Optional[float] = None
    capacity_40ft_mt: Optional[float] = None
    capacity_40ft_hc_mt: Optional[float] = None


# --- FOB Prices ---

class FobPriceCreate(BaseModel):
    grade_id: uuid.UUID
    origin_port_id: uuid.UUID
    price_date: date
    price_usd_per_kg: Optional[float] = None
    price_usd_per_mt: Optional[float] = None
    currency: str = "USD"
    notes: Optional[str] = None


class FobPriceResponse(BaseModel):
    id: str
    grade_id: str
    grade_name: Optional[str] = None
    product_name: Optional[str] = None
    variety_name: Optional[str] = None
    origin_port_id: str
    origin_port_name: Optional[str] = None
    price_date: str
    price_usd_per_kg: Optional[float] = None
    price_usd_per_mt: Optional[float] = None
    currency: str = "USD"
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class FobPriceBulkCreate(BaseModel):
    prices: List[FobPriceCreate]


# --- Freight Rates ---

class FreightRateCreate(BaseModel):
    origin_port_id: uuid.UUID
    destination_port_id: uuid.UUID
    container_type: str = "20ft"
    rate_usd: Optional[float] = None
    transit_days: Optional[int] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None


class FreightRateResponse(BaseModel):
    id: str
    origin_port_name: Optional[str] = None
    origin_port_country: Optional[str] = None
    destination_port_name: Optional[str] = None
    destination_port_country: Optional[str] = None
    container_type: str
    rate_usd: Optional[float] = None
    transit_days: Optional[int] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# --- Tenant Defaults ---

class TenantDefaultsUpdate(BaseModel):
    default_origin_port_id: Optional[uuid.UUID] = None
    default_currency: Optional[str] = None
    default_container_type: Optional[str] = None
    default_payment_terms: Optional[str] = None
    supported_incoterms: Optional[List[str]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class TenantDefaultsResponse(BaseModel):
    default_origin_port_id: Optional[str] = None
    default_origin_port_name: Optional[str] = None
    default_currency: str = "USD"
    default_container_type: str = "20ft"
    default_payment_terms: Optional[str] = None
    supported_incoterms: Optional[list] = None
    custom_settings: Optional[dict] = None

    class Config:
        from_attributes = True


# --- CFR Calculator ---

class CfrCalculateRequest(BaseModel):
    grade_id: uuid.UUID
    destination_port_id: uuid.UUID
    origin_port_id: Optional[uuid.UUID] = None
    quantity_mt: float = 1.0
    container_type: str = "20ft"
    price_date: Optional[date] = None


class CfrCalculateResponse(BaseModel):
    fob_price_per_mt: Optional[float] = None
    freight_per_container: Optional[float] = None
    freight_per_mt: Optional[float] = None
    cfr_price_per_mt: Optional[float] = None
    total_value: Optional[float] = None
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    product: Optional[str] = None
    variety: Optional[str] = None
    grade: Optional[str] = None
    price_date: Optional[str] = None
    container_type: str = "20ft"
    container_capacity_mt: Optional[float] = None
    quantity_mt: float = 1.0
    packaging: Optional[str] = None
    moq_mt: Optional[float] = None
    notes: Optional[str] = None
