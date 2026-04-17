"""Pydantic schemas for Shipment Intelligence."""
from typing import Dict, List, Optional

from pydantic import BaseModel


class ShipmentResponse(BaseModel):
    id: str
    company_id: str
    shipment_date: str
    direction: str
    commodity_text: str
    hs_code: Optional[str] = None
    origin_country: str
    destination_country: str
    origin_port_text: Optional[str] = None
    destination_port_text: Optional[str] = None
    volume_mt: Optional[float] = None
    unit_price_usd_per_mt: Optional[float] = None
    value_usd: Optional[float] = None
    trade_partner_name: Optional[str] = None
    trade_partner_country: Optional[str] = None
    matched_product_id: Optional[str] = None
    match_confidence: Optional[float] = None
    created_at: str


class ShipmentSummaryResponse(BaseModel):
    company_id: str
    last_refreshed_at: Optional[str] = None
    data_through_date: Optional[str] = None
    source_providers: list = []
    role: Optional[str] = None
    cadence: Optional[str] = None
    totals: dict = {}
    monthly_series: list = []
    top_partners: list = []
    top_lanes: list = []
    top_commodities: list = []
    catalog_match_ratio: float = 0.0


class ShipmentPartnerResponse(BaseModel):
    name: str
    country: Optional[str] = None
    company_id: Optional[str] = None
    shipments: int = 0
    volume_mt: float = 0


class ShipmentCommodityResponse(BaseModel):
    name: str
    hs: Optional[str] = None
    matched_product_id: Optional[str] = None
    shipments: int = 0
    volume_mt: float = 0
    avg_price: Optional[float] = None
    last_date: Optional[str] = None
