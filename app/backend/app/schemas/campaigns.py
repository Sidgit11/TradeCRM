from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class CampaignStepCreate(BaseModel):
    channel: str  # email | whatsapp
    delay_days: int = 0
    condition: str = "always"  # no_reply | no_open | always
    template_content: Optional[str] = None
    whatsapp_template_name: Optional[str] = None
    subject_template: Optional[str] = None


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str  # email | whatsapp | multi_channel
    contact_list_id: Optional[uuid.UUID] = None
    steps: List[CampaignStepCreate] = []
    settings: Dict[str, Any] = {}


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class CampaignStepResponse(BaseModel):
    id: str
    step_number: int
    channel: str
    delay_days: int
    condition: str
    template_content: Optional[str] = None
    whatsapp_template_name: Optional[str] = None
    subject_template: Optional[str] = None

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    type: str
    status: str
    contact_list_id: Optional[str] = None
    created_by: str
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    settings: dict = {}
    steps: List[CampaignStepResponse] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CampaignStepReorder(BaseModel):
    step_ids: List[uuid.UUID]


class MessagePreview(BaseModel):
    contact_id: str
    contact_name: str
    channel: str
    subject: Optional[str] = None
    body: str
    status: str = "pending_approval"


class CampaignAnalytics(BaseModel):
    total_sent: int = 0
    delivered: int = 0
    delivery_rate: float = 0
    opened: int = 0
    open_rate: float = 0
    replied: int = 0
    reply_rate: float = 0
    failed: int = 0
    bounced: int = 0
