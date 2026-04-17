"""Pydantic schemas for AI Insights."""
from typing import List, Optional

from pydantic import BaseModel


class InsightItem(BaseModel):
    icon: str  # "clock", "warning", "envelope", "package", "truck", "sparkle", "fire", "lightbulb"
    title: str
    body: str
    action_label: Optional[str] = None
    action_type: Optional[str] = None  # "draft_followup", "open_inbox", "open_leads", "create_opportunity", "infer_interests", "send_price_update"
    priority: int = 3  # 1=urgent, 2=important, 3=informational


class InsightsResponse(BaseModel):
    entity_type: str
    entity_id: str
    insights: List[InsightItem]
    generated_at: str
    cached: bool = False
