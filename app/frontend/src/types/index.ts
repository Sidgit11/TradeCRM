// ─── Enums ──────────────────────────────────────────────────────────
export type PlanType = "free_trial" | "starter" | "growth" | "pro";
export type UserRole = "admin" | "member";
export type EnrichmentStatus = "not_enriched" | "enriching" | "partially_enriched" | "enriched";
export type ContactEnrichmentStatus = "not_enriched" | "enriching" | "enriched";
export type ContactSource = "manual" | "import" | "discovery" | "enrichment";
export type CompanySource = "discovery" | "manual" | "import";
export type CampaignType = "email" | "whatsapp" | "multi_channel";
export type CampaignStatus = "draft" | "active" | "paused" | "completed" | "cancelled";
export type ChannelType = "email" | "whatsapp";
export type StepCondition = "no_reply" | "no_open" | "always";
export type MessageDirection = "outbound" | "inbound";
export type MessageStatus = "queued" | "sending" | "sent" | "delivered" | "opened" | "clicked" | "replied" | "failed" | "bounced";
export type ReplyClassification = "interested" | "price_inquiry" | "sample_request" | "meeting_request" | "not_interested" | "auto_reply" | "out_of_office";
export type SuggestionStatus = "pending" | "approved" | "edited" | "rejected" | "sent";
export type SequenceStatus = "active" | "completed" | "replied" | "unsubscribed" | "paused";
export type OpportunitySource = "discovery" | "campaign" | "manual";
export type ActorType = "user" | "agent" | "system";
export type AgentTaskType = "buyer_discovery" | "company_research" | "contact_enrichment" | "message_compose" | "reply_suggest" | "campaign_analytics";
export type AgentTaskStatus = "pending" | "running" | "completed" | "failed";
export type AgentStepStatus = "pending" | "active" | "completed" | "failed";

// ─── Contact ────────────────────────────────────────────────────────

export interface Contact {
  id: string;
  tenant_id: string;
  salutation: string | null;
  name: string;
  email: string | null;
  secondary_email: string | null;
  phone: string | null;
  secondary_phone: string | null;
  whatsapp_number: string | null;
  country: string | null;
  city: string | null;
  company_name: string | null;
  company_id: string | null;
  title: string | null;
  department: string | null;
  is_decision_maker: boolean;
  preferred_language: string | null;
  preferred_channel: string | null;
  timezone: string | null;
  do_not_contact: boolean;
  linkedin_url: string | null;
  avatar_url: string | null;
  tags: string[];
  custom_fields: Record<string, string>;
  opted_in_whatsapp: boolean;
  opted_in_email: boolean;
  enrichment_status: string;
  source: string;
  total_interactions: number;
  first_seen_at: string | null;
  last_interaction_at: string | null;
  last_contacted_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactList {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  member_count?: number;
  created_at: string;
}

// ─── Company ────────────────────────────────────────────────────────

export interface Company {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  country: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  industry: string | null;
  company_type: string | null;
  company_size: string | null;
  year_established: number | null;
  number_of_employees: string | null;
  annual_revenue_usd: number | null;
  registration_number: string | null;
  commodities: string[];
  preferred_origins: string[] | null;
  preferred_incoterms: string | null;
  preferred_payment_terms: string | null;
  certifications_required: string[] | null;
  destination_ports: string[] | null;
  import_volume_annual: number | null;
  shipment_frequency: string | null;
  last_shipment_date: string | null;
  bank_name: string | null;
  bank_country: string | null;
  bank_swift_code: string | null;
  linkedin_url: string | null;
  logo_url: string | null;
  tax_id: string | null;
  rating: string | null;
  tags: string[] | null;
  known_suppliers: string[] | null;
  trade_references: unknown[] | null;
  social_media: Record<string, string> | null;
  enrichment_status: string;
  enrichment_data: Record<string, unknown> | null;
  confidence_score: number | null;
  source: string;
  first_contact_date: string | null;
  last_interaction_at: string | null;
  total_inquiries: number;
  total_deals_won: number;
  total_revenue: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Pipeline ───────────────────────────────────────────────────────

export interface PipelineStage {
  id: string;
  name: string;
  slug: string;
  order: number;
  color: string;
}

export interface PipelineOpportunity {
  id: string;
  display_id: string | null;
  tenant_id: string;
  title: string | null;
  company_id: string;
  company_name: string | null;
  contact_id: string | null;
  contact_name: string | null;
  stage_id: string;
  stage_name: string | null;
  stage_color: string | null;
  source: string;
  value: number | null;
  commodity: string | null;
  quantity_mt: number | null;
  target_price: number | null;
  our_price: number | null;
  competitor_price: number | null;
  estimated_value_usd: number | null;
  incoterms: string | null;
  payment_terms: string | null;
  container_type: string | null;
  number_of_containers: number | null;
  target_shipment_date: string | null;
  shipping_line: string | null;
  packaging_requirements: string | null;
  quality_specifications: Record<string, string> | null;
  expected_close_date: string | null;
  follow_up_date: string | null;
  probability: number;
  sample_sent: boolean;
  sample_approved: boolean | null;
  sample_feedback: string | null;
  currency: string;
  loss_reason: string | null;
  notes: string | null;
  assigned_to: string | null;
  tags: string[] | null;
  is_archived: boolean;
  sample_sent_date: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Campaign ───────────────────────────────────────────────────────

export interface CampaignStep {
  id: string;
  campaign_id: string;
  step_number: number;
  channel: ChannelType;
  delay_days: number;
  condition: StepCondition;
  template_content: string | null;
  whatsapp_template_name: string | null;
  subject_template: string | null;
}

export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  type: CampaignType;
  status: CampaignStatus;
  contact_list_id: string | null;
  created_by: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  settings: Record<string, unknown>;
  steps?: CampaignStep[];
  created_at: string;
}

export interface CampaignAnalytics {
  total_sent: number;
  delivered: number;
  delivery_rate: number;
  opened: number;
  open_rate: number;
  replied: number;
  reply_rate: number;
  failed: number;
  bounced: number;
}

// ─── Message ────────────────────────────────────────────────────────

export interface Message {
  id: string;
  campaign_id: string | null;
  tenant_id: string;
  contact_id: string;
  sent_by: string | null;
  channel: ChannelType;
  direction: MessageDirection;
  subject: string | null;
  body: string;
  status: MessageStatus;
  external_id: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  replied_at: string | null;
  failed_reason: string | null;
  created_at: string;
}

export interface ReplySuggestion {
  id: string;
  message_id: string;
  classification: ReplyClassification;
  suggested_reply_text: string;
  explanation: string | null;
  confidence: number;
  status: SuggestionStatus;
  edited_text: string | null;
  created_at: string;
}

// ─── Leads ──────────────────────────────────────────────────────────

export interface InboundLead {
  id: string;
  tenant_id: string;
  email_account_id: string;
  gmail_message_id: string;
  gmail_thread_id: string;
  classification: string;
  non_lead_reason: string | null;
  confidence: number | null;
  sender_name: string | null;
  sender_email: string;
  sender_phone: string | null;
  sender_company: string | null;
  sender_designation: string | null;
  matched_contact_id: string | null;
  matched_contact_confidence: number | null;
  matched_company_id: string | null;
  matched_company_confidence: number | null;
  subject: string | null;
  body_preview: string | null;
  body_full: string | null;
  received_at: string | null;
  thread_message_count: number;
  products_mentioned: unknown[] | null;
  quantities: Record<string, string> | null;
  target_price: string | null;
  delivery_terms: string | null;
  destination: string | null;
  urgency: string | null;
  specific_questions: string | null;
  language: string | null;
  status: string;
  is_high_value: boolean;
  draft_reply: string | null;
  draft_reply_explanation: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadStats {
  total: number;
  leads: number;
  non_leads: number;
  new: number;
  high_value: number;
}

export interface EmailAccount {
  id: string;
  email_address: string;
  provider: string;
  display_name: string;
  is_active: boolean;
  last_sync_at: string | null;
  created_at: string;
}

// ─── Catalog ────────────────────────────────────────────────────────

export interface CommodityRef {
  name: string;
  hs_codes: string[];
  aliases: string[];
  category: string | null;
  default_capacity_20ft_mt: string | null;
  default_capacity_40ft_mt: string | null;
}

export interface ProductGrade {
  id: string;
  name: string;
  specifications: Record<string, string> | null;
  packaging_type: string | null;
  packaging_weight_kg: number | null;
  moq_mt: number | null;
}

export interface ProductVariety {
  id: string;
  name: string;
  grades: ProductGrade[];
}

export interface Product {
  id: string;
  name: string;
  origin_country: string;
  hs_code: string | null;
  description: string | null;
  shelf_life_days: number | null;
  certifications: string[] | null;
  aliases: string[] | null;
  capacity_20ft_mt: number | null;
  capacity_40ft_mt: number | null;
  capacity_40ft_hc_mt: number | null;
  varieties: ProductVariety[];
  created_at: string;
}

// ─── Tenant / User ──────────────────────────────────────────────────

export interface Tenant {
  id: string;
  company_name: string;
  domain: string | null;
  plan: PlanType;
  commodities: string[];
  target_markets: string[];
  certifications: string[];
  about: string | null;
  created_at: string;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  last_active_at: string | null;
  created_at: string;
}

// ─── Agent ──────────────────────────────────────────────────────────

export interface AgentStep {
  name: string;
  status: AgentStepStatus;
  detail: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// ─── Shipments ─────────────────────────────────────────────────────

export interface ShipmentRecord {
  id: string;
  company_id: string;
  shipment_date: string;
  direction: "import" | "export";
  commodity_text: string;
  hs_code: string | null;
  origin_country: string;
  destination_country: string;
  origin_port_text: string | null;
  destination_port_text: string | null;
  volume_mt: number | null;
  unit_price_usd_per_mt: number | null;
  value_usd: number | null;
  trade_partner_name: string | null;
  trade_partner_country: string | null;
  matched_product_id: string | null;
  match_confidence: number | null;
  created_at: string;
}

export interface ShipmentSummary {
  company_id: string;
  last_refreshed_at: string | null;
  data_through_date: string | null;
  source_providers: string[];
  role: string | null;
  cadence: string | null;
  totals: {
    shipments_12mo: number;
    volume_12mo_mt: number;
    value_12mo_usd: number;
    total_shipments: number;
    total_volume_mt: number;
    avg_unit_price_usd_per_mt: number | null;
    price_range: [number, number] | null;
  };
  monthly_series: { month: string; volume_mt: number; shipments: number }[];
  top_partners: { name: string; country?: string; company_id?: string; shipments: number; volume_mt: number }[];
  top_lanes: { origin_port: string; destination_port: string; shipments: number; volume_mt: number }[];
  top_commodities: { name: string; hs?: string; matched_product_id?: string; shipments: number; volume_mt: number; avg_price?: number; last_date?: string }[];
  catalog_match_ratio: number;
}

// ─── Product-Port Interests ────────────────────────────────────────

export interface ProductPortInterest {
  id: string;
  tenant_id: string;
  company_id: string | null;
  contact_id: string | null;
  product_id: string;
  product_name: string | null;
  variety_id: string | null;
  variety_name: string | null;
  grade_id: string | null;
  grade_name: string | null;
  destination_port_id: string | null;
  destination_port_name: string | null;
  origin_port_id: string | null;
  origin_port_name: string | null;
  role: string;
  source: string;
  confidence: number | null;
  confidence_level: string | null;
  evidence: Record<string, unknown> | null;
  status: string;
  confirmed_by: string | null;
  confirmed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ─── AI Insights ───────────────────────────────────────────────────

export interface InsightItem {
  icon: string;
  title: string;
  body: string;
  action_label: string | null;
  action_type: string | null;
  priority: number;
}

export interface InsightsResponse {
  entity_type: string;
  entity_id: string;
  insights: InsightItem[];
  generated_at: string;
  cached: boolean;
}

// ─── Message Templates ─────────────────────────────────────────────

export type TemplateChannel = "email" | "whatsapp";
export type TemplateCategory = "introduction" | "price_update" | "follow_up" | "sample_offer" | "order_confirmation" | "festive_greeting" | "reactivation" | "custom";

export interface MessageTemplate {
  id: string;
  tenant_id: string;
  created_by: string | null;
  name: string;
  channel: TemplateChannel;
  category: TemplateCategory;
  subject: string | null;
  body: string;
  body_format: string;
  variables: string[];
  description: string | null;
  is_archived: boolean;
  is_default: boolean;
  ai_generated: boolean;
  ai_prompt: string | null;
  last_used_at: string | null;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateVariable {
  key: string;
  source: string;
  example: string;
  fallback: string;
  description: string;
}

// ─── Agent Tasks ───────────────────────────────────────────────────

export interface AgentTask {
  id: string;
  tenant_id: string;
  task_type: AgentTaskType;
  status: AgentTaskStatus;
  steps: AgentStep[];
  current_step_index: number;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  error: string | null;
  credits_consumed: number;
  created_at: string;
  completed_at: string | null;
}

// ─── Activity ───────────────────────────────────────────────────────

export interface ActivityLog {
  id: string;
  tenant_id: string;
  actor_type: ActorType;
  actor_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

// ─── API Helpers ────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface WSEvent {
  type: string;
  data: Record<string, unknown>;
}
