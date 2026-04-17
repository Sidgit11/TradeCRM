import enum


class PlanType(str, enum.Enum):
    free_trial = "free_trial"
    starter = "starter"
    growth = "growth"
    pro = "pro"


class UserRole(str, enum.Enum):
    admin = "admin"
    member = "member"


class EnrichmentStatus(str, enum.Enum):
    not_enriched = "not_enriched"
    enriching = "enriching"
    partially_enriched = "partially_enriched"
    enriched = "enriched"


class ContactEnrichmentStatus(str, enum.Enum):
    not_enriched = "not_enriched"
    enriching = "enriching"
    enriched = "enriched"


class ContactSource(str, enum.Enum):
    manual = "manual"
    import_ = "import"
    discovery = "discovery"
    enrichment = "enrichment"


class CompanySource(str, enum.Enum):
    discovery = "discovery"
    manual = "manual"
    import_ = "import"


class CampaignType(str, enum.Enum):
    email = "email"
    whatsapp = "whatsapp"
    multi_channel = "multi_channel"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class ChannelType(str, enum.Enum):
    email = "email"
    whatsapp = "whatsapp"


class StepCondition(str, enum.Enum):
    no_reply = "no_reply"
    no_open = "no_open"
    always = "always"


class MessageDirection(str, enum.Enum):
    outbound = "outbound"
    inbound = "inbound"


class MessageStatus(str, enum.Enum):
    queued = "queued"
    sending = "sending"
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    failed = "failed"
    bounced = "bounced"


class MessageEventType(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"
    bounced = "bounced"
    failed = "failed"
    read = "read"
    replied = "replied"


class ReplyClassification(str, enum.Enum):
    interested = "interested"
    price_inquiry = "price_inquiry"
    sample_request = "sample_request"
    meeting_request = "meeting_request"
    not_interested = "not_interested"
    auto_reply = "auto_reply"
    out_of_office = "out_of_office"


class SuggestionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    edited = "edited"
    rejected = "rejected"
    sent = "sent"


class SequenceStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    replied = "replied"
    unsubscribed = "unsubscribed"
    paused = "paused"


class OpportunitySource(str, enum.Enum):
    manual = "manual"
    inbound_email = "inbound_email"
    campaign = "campaign"
    discovery = "discovery"
    referral = "referral"
    whatsapp = "whatsapp"
    trade_show = "trade_show"


class TemplateChannel(str, enum.Enum):
    email = "email"
    whatsapp = "whatsapp"


class TemplateCategory(str, enum.Enum):
    introduction = "introduction"
    price_update = "price_update"
    follow_up = "follow_up"
    sample_offer = "sample_offer"
    order_confirmation = "order_confirmation"
    festive_greeting = "festive_greeting"
    reactivation = "reactivation"
    custom = "custom"


class ShipmentDirection(str, enum.Enum):
    import_ = "import"
    export = "export"


class TradeRole(str, enum.Enum):
    importer = "importer"
    exporter = "exporter"
    re_exporter = "re_exporter"
    both = "both"
    unknown = "unknown"


class ShipmentCadence(str, enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    biannual = "biannual"
    annual = "annual"
    irregular = "irregular"
    none_ = "none"


class InterestRole(str, enum.Enum):
    buyer = "buyer"
    seller = "seller"
    both = "both"


class InterestSource(str, enum.Enum):
    manual = "manual"
    shipment_data = "shipment_data"
    email_thread = "email_thread"
    whatsapp_thread = "whatsapp_thread"
    enrichment = "enrichment"
    campaign_reply = "campaign_reply"
    onboarding_import = "onboarding_import"


class ConfidenceLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class InterestStatus(str, enum.Enum):
    suggested = "suggested"
    confirmed = "confirmed"
    rejected = "rejected"
    stale = "stale"


class ActorType(str, enum.Enum):
    user = "user"
    agent = "agent"
    system = "system"


class CreditActionType(str, enum.Enum):
    genie_query = "genie_query"
    enrichment = "enrichment"
    ai_compose = "ai_compose"
    ai_reply = "ai_reply"


class AgentTaskType(str, enum.Enum):
    buyer_discovery = "buyer_discovery"
    company_research = "company_research"
    contact_enrichment = "contact_enrichment"
    message_compose = "message_compose"
    reply_suggest = "reply_suggest"
    campaign_analytics = "campaign_analytics"


class AgentTaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
