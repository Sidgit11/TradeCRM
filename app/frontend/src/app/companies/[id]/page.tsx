"use client";
import type { Company, PipelineOpportunity, InboundLead, ShipmentSummary, ProductPortInterest, ShipmentRecord, InsightsResponse, InsightItem } from "@/types";

import { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Modal } from "@/components/ui/Modal";
import {
  ArrowLeft, PencilSimple, Buildings, MapPin, Globe, Phone,
  EnvelopeSimple, Calendar, Users, CurrencyDollar, Bank,
  Anchor, Package, Certificate, Truck, Star, Notebook,
  LinkedinLogo, IdentificationCard, Scales, ArrowsClockwise,
  Kanban, UserFocus, ArrowRight, Compass, Check, X as XIcon,
  Sparkle, CircleDashed, SealCheck, CircleNotch,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { ProductPicker } from "@/components/ui/ProductPicker";
import { Tooltip } from "@/components/ui/Tooltip";
import { EnrichmentPanel } from "@/components/agentic/EnrichmentPanel";
import { toast } from "sonner";
import { formatRelativeTime, formatNumber } from "@/lib/utils";


const COMPANY_TYPES = ["importer", "distributor", "manufacturer", "broker", "retailer", "agent", "re-exporter", "end_user", "other"];
const EMPLOYEE_RANGES = ["1-10", "11-50", "51-200", "201-500", "500+"];
const INCOTERMS = ["FOB", "CFR", "CIF", "CnF", "EXW", "DDP"];
const PAYMENT_TERMS = ["LC at Sight", "TT Advance", "CAD", "DA", "Open Account", "LC 30 Days", "LC 60 Days", "LC 90 Days"];
const SHIPMENT_FREQ = ["monthly", "quarterly", "biannual", "annual", "ad-hoc"];

function InfoRow({ icon: Icon, label, value, href }: { icon: React.ElementType; label: string; value: string | number | null | undefined; href?: string }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="h-4 w-4 text-text-tertiary mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-[11px] text-text-tertiary uppercase tracking-wide">{label}</p>
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline break-all">{String(value)}</a>
        ) : (
          <p className="text-sm text-text-primary break-all">{String(value)}</p>
        )}
      </div>
    </div>
  );
}

function TagList({ items, label }: { items: string[] | null | undefined; label: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="py-2">
      <p className="text-[11px] text-text-tertiary uppercase tracking-wide mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => <Badge key={item} size="sm">{item}</Badge>)}
      </div>
    </div>
  );
}

export default function CompanyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [showEdit, setShowEdit] = useState(false);
  const [editSection, setEditSection] = useState("");
  const [saving, setSaving] = useState(false);
  const [editData, setEditData] = useState<Record<string, string>>({});
  const [editCommodities, setEditCommodities] = useState<string[]>([]);
  const [opportunities, setOpportunities] = useState<PipelineOpportunity[]>([]);
  const [leads, setLeads] = useState<InboundLead[]>([]);
  const [shipmentSummary, setShipmentSummary] = useState<ShipmentSummary | null>(null);
  const [interests, setInterests] = useState<ProductPortInterest[]>([]);
  const [inferring, setInferring] = useState(false);
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [enrichTaskId, setEnrichTaskId] = useState<string | null>(null);
  const [enrichmentsRemaining, setEnrichmentsRemaining] = useState<number | null>(null);
  const [showEnrichPanel, setShowEnrichPanel] = useState(false);

  const fetchCompany = useCallback(async () => {
    setLoading(true);
    try {
      const [companyRes, oppsRes, leadsRes, shipRes, intRes] = await Promise.all([
        api.get<Company>(`/companies/${id}`),
        api.get<PipelineOpportunity[]>(`/pipeline?company_id=${id}&active_only=true`),
        api.get<{ items: InboundLead[] }>(`/leads?tab=all&company_id=${id}&active_only=true&limit=20`),
        api.get<ShipmentSummary>(`/companies/${id}/shipments/summary`).catch(() => ({ data: null })),
        api.get<ProductPortInterest[]>(`/interests?company_id=${id}`).catch(() => ({ data: [] })),
      ]);
      setCompany(companyRes.data);
      setOpportunities(oppsRes.data);
      setLeads(leadsRes.data.items || []);
      if (shipRes.data) setShipmentSummary(shipRes.data as ShipmentSummary);
      setInterests((intRes.data as ProductPortInterest[]) || []);
    } catch { toast.error("Failed to load company"); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchCompany(); }, [fetchCompany]);

  // Fetch insights separately (non-blocking)
  useEffect(() => {
    if (!id) return;
    setInsightsLoading(true);
    api.get<InsightsResponse>(`/insights/company/${id}`)
      .then(({ data }) => setInsights(data.insights || []))
      .catch(() => {})
      .finally(() => setInsightsLoading(false));
  }, [id]);

  const handleEnrich = async () => {
    setEnriching(true);
    try {
      const { data } = await api.post<{
        agent_task_id: string;
        company_id: string;
        status: string;
        enrichments_remaining: number;
      }>(`/companies/${id}/enrich`, {});
      setEnrichTaskId(data.agent_task_id);
      setEnrichmentsRemaining(data.enrichments_remaining);
      setShowEnrichPanel(true);
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to start enrichment"));
    }
    setEnriching(false);
  };

  const handleEnrichComplete = useCallback(() => {
    setShowEnrichPanel(false);
    setEnrichTaskId(null);
    fetchCompany();
    toast.success("Company enriched successfully");
  }, [fetchCompany]);

  const openEdit = (section: string) => {
    if (!company) return;
    const c = company;
    const data: Record<string, string> = {};

    if (section === "basic") {
      data.name = c.name || ""; data.description = c.description || "";
      data.country = c.country || ""; data.city = c.city || ""; data.state = c.state || "";
      data.postal_code = c.postal_code || ""; data.address = c.address || "";
      data.phone = c.phone || ""; data.email = c.email || "";
      data.website = c.website || ""; data.industry = c.industry || "";
    } else if (section === "business") {
      data.company_type = c.company_type || ""; data.company_size = c.company_size || "";
      data.year_established = c.year_established?.toString() || "";
      data.number_of_employees = c.number_of_employees || "";
      data.annual_revenue_usd = c.annual_revenue_usd?.toString() || "";
      data.registration_number = c.registration_number || "";
      data.tax_id = c.tax_id || "";
      data.rating = c.rating || "";
    } else if (section === "trade") {
      setEditCommodities(c.commodities || []);
      data.preferred_origins = (c.preferred_origins || []).join(", ");
      data.preferred_incoterms = c.preferred_incoterms || "";
      data.preferred_payment_terms = c.preferred_payment_terms || "";
      data.certifications_required = (c.certifications_required || []).join(", ");
      data.destination_ports = (c.destination_ports || []).join(", ");
      data.import_volume_annual = c.import_volume_annual?.toString() || "";
      data.shipment_frequency = c.shipment_frequency || "";
    } else if (section === "banking") {
      data.bank_name = c.bank_name || ""; data.bank_country = c.bank_country || "";
      data.bank_swift_code = c.bank_swift_code || "";
      data.known_suppliers = (c.known_suppliers || []).join(", ");
    } else if (section === "additional") {
      data.linkedin_url = c.linkedin_url || "";
      data.tags = (c.tags || []).join(", ");
      data.notes = c.notes || "";
    }

    setEditData(data);
    setEditSection(section);
    setShowEdit(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const csvToArr = (s: string) => s ? s.split(",").map((v) => v.trim()).filter(Boolean) : undefined;
      const payload: Record<string, unknown> = {};

      if (editSection === "basic") {
        Object.assign(payload, {
          name: editData.name?.trim(), description: editData.description?.trim() || null,
          country: editData.country?.trim() || null, city: editData.city?.trim() || null,
          state: editData.state?.trim() || null, postal_code: editData.postal_code?.trim() || null,
          address: editData.address?.trim() || null,
          phone: editData.phone?.trim() || null, email: editData.email?.trim() || null,
          website: editData.website?.trim() || null, industry: editData.industry?.trim() || null,
        });
      } else if (editSection === "business") {
        Object.assign(payload, {
          company_type: editData.company_type || null, company_size: editData.company_size || null,
          year_established: editData.year_established ? parseInt(editData.year_established) : null,
          number_of_employees: editData.number_of_employees || null,
          annual_revenue_usd: editData.annual_revenue_usd ? parseFloat(editData.annual_revenue_usd) : null,
          registration_number: editData.registration_number?.trim() || null,
          tax_id: editData.tax_id?.trim() || null,
          rating: editData.rating || null,
        });
      } else if (editSection === "trade") {
        Object.assign(payload, {
          commodities: editCommodities,
          preferred_origins: csvToArr(editData.preferred_origins || ""),
          preferred_incoterms: editData.preferred_incoterms || null,
          preferred_payment_terms: editData.preferred_payment_terms || null,
          certifications_required: csvToArr(editData.certifications_required || ""),
          destination_ports: csvToArr(editData.destination_ports || ""),
          import_volume_annual: editData.import_volume_annual ? parseFloat(editData.import_volume_annual) : null,
          shipment_frequency: editData.shipment_frequency || null,
        });
      } else if (editSection === "banking") {
        Object.assign(payload, {
          bank_name: editData.bank_name?.trim() || null,
          bank_country: editData.bank_country?.trim() || null,
          bank_swift_code: editData.bank_swift_code?.trim() || null,
          known_suppliers: csvToArr(editData.known_suppliers || ""),
        });
      } else if (editSection === "additional") {
        Object.assign(payload, {
          linkedin_url: editData.linkedin_url?.trim() || null,
          tags: csvToArr(editData.tags || ""),
          notes: editData.notes?.trim() || null,
        });
      }

      await api.put(`/companies/${id}`, payload);
      toast.success("Company updated");
      setShowEdit(false);
      fetchCompany();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to update company")); }
    setSaving(false);
  };

  const setEd = (k: string, v: string) => setEditData((d) => ({ ...d, [k]: v }));

  const ChipSelect = ({ options, field, label }: { options: string[]; field: string; label?: string }) => (
    <div>
      {label && <p className="text-[13px] font-medium text-text-primary mb-1.5">{label}</p>}
      <div className="flex flex-wrap gap-1.5">
        {options.map((t) => (
          <button key={t} onClick={() => setEd(field, editData[field] === t ? "" : t)}
            className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer capitalize ${
              editData[field] === t ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
            }`}>{t}</button>
        ))}
      </div>
    </div>
  );

  if (loading) {
    return <AppShell title="Company"><FullWidthLayout><Skeleton variant="card" className="h-32 mb-4" /><Skeleton variant="card" className="h-64" /></FullWidthLayout></AppShell>;
  }

  if (!company) {
    return <AppShell title="Company"><FullWidthLayout><p className="text-sm text-text-secondary">Company not found</p></FullWidthLayout></AppShell>;
  }

  const c = company;

  return (
    <AppShell title={c.name}>
      <FullWidthLayout>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/companies")} className="text-text-tertiary hover:text-text-primary cursor-pointer">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{c.name}</h2>
                {c.company_type && <Badge size="md" variant="outline" className="capitalize">{c.company_type}</Badge>}
                {c.rating && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    c.rating === "hot" ? "bg-error/10 text-red-700" :
                    c.rating === "warm" ? "bg-warning/10 text-amber-700" : "bg-info/10 text-blue-700"
                  }`}>{c.rating}</span>
                )}
              </div>
              {c.description && <p className="text-sm text-text-secondary mt-0.5">{c.description}</p>}
              <p className="text-xs text-text-tertiary mt-0.5">
                Added {formatRelativeTime(c.created_at)} via {c.source}
                {c.last_interaction_at && ` / Last interaction ${formatRelativeTime(c.last_interaction_at)}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {c.enrichment_status === "enriched" ? (
              <Tooltip content="Company is already enriched. Click to re-enrich.">
                <Button variant="secondary" size="sm" onClick={handleEnrich} isLoading={enriching}>
                  <SealCheck className="h-4 w-4 text-success" /> Re-enrich
                </Button>
              </Tooltip>
            ) : c.enrichment_status === "enriching" ? (
              <Button variant="secondary" size="sm" disabled>
                <CircleNotch className="h-4 w-4 animate-spin" /> Enriching...
              </Button>
            ) : enrichmentsRemaining !== null && enrichmentsRemaining <= 0 ? (
              <Tooltip content="No enrichment credits remaining. Upgrade your plan.">
                <span tabIndex={0}>
                  <Button variant="secondary" size="sm" disabled>
                    <Sparkle className="h-4 w-4" weight="fill" /> Enrich
                  </Button>
                </span>
              </Tooltip>
            ) : (
              <div className="relative">
                <Button variant="primary" size="sm" onClick={handleEnrich} isLoading={enriching}>
                  <Sparkle className="h-4 w-4" weight="fill" /> Enrich
                </Button>
                {enrichmentsRemaining !== null && enrichmentsRemaining > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 flex items-center justify-center h-4 min-w-[16px] px-1 text-[9px] font-bold text-text-inverse bg-primary rounded-full border-2 border-surface">
                    {enrichmentsRemaining}
                  </span>
                )}
              </div>
            )}
            <Button variant="ghost" onClick={fetchCompany}><ArrowsClockwise className="h-4 w-4 mr-1" /> Refresh</Button>
          </div>
        </div>

        {/* AI Insights */}
        {(insights.length > 0 || insightsLoading) && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide flex items-center gap-1">
                <Sparkle className="h-3.5 w-3.5 text-warning" /> AI Insights
              </h3>
              <button onClick={() => {
                setInsightsLoading(true);
                api.post<InsightsResponse>(`/insights/company/${id}/refresh`, {})
                  .then(({ data }) => setInsights(data.insights || []))
                  .catch(() => {})
                  .finally(() => setInsightsLoading(false));
              }} className="text-[10px] text-primary hover:underline cursor-pointer">Refresh</button>
            </div>
            {insightsLoading ? (
              <div className="animate-pulse space-y-2">{[1, 2].map((i) => <div key={i} className="h-14 bg-border-light rounded-[var(--radius-md)]" />)}</div>
            ) : (
              <div className="space-y-2">
                {insights.map((insight, idx) => {
                  const iconMap: Record<string, string> = { clock: "\u23f0", warning: "\u26a0\ufe0f", envelope: "\u2709\ufe0f", package: "\ud83d\udce6", truck: "\ud83d\ude9a", sparkle: "\u2728", fire: "\ud83d\udd25", lightbulb: "\ud83d\udca1" };
                  return (
                    <div key={idx} className={`flex items-start gap-3 p-3 rounded-[var(--radius-md)] border ${
                      insight.priority === 1 ? "border-warning/30 bg-warning/5" : insight.priority === 2 ? "border-primary/20 bg-primary/5" : "border-border bg-surface"
                    }`}>
                      <span className="text-base mt-0.5">{iconMap[insight.icon] || "\ud83d\udca1"}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary">{insight.title}</p>
                        <p className="text-xs text-text-secondary mt-0.5">{insight.body}</p>
                      </div>
                      {insight.action_label && (
                        <button className="shrink-0 px-3 py-1 text-xs font-medium text-primary bg-primary/10 rounded-[var(--radius-sm)] hover:bg-primary/20 transition-colors cursor-pointer">
                          {insight.action_label}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Card className="p-3 text-center cursor-pointer hover:shadow-[var(--shadow-md)] transition-shadow" onClick={() => opportunities.length > 0 && document.getElementById("linked-opps")?.scrollIntoView({ behavior: "smooth" })}>
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-primary">{opportunities.length}</p>
            <p className="text-xs text-text-tertiary">Active Opportunities</p>
          </Card>
          <Card className="p-3 text-center cursor-pointer hover:shadow-[var(--shadow-md)] transition-shadow" onClick={() => leads.length > 0 && document.getElementById("linked-leads")?.scrollIntoView({ behavior: "smooth" })}>
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{leads.length}</p>
            <p className="text-xs text-text-tertiary">Active Leads</p>
          </Card>
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-success">{c.total_deals_won}</p>
            <p className="text-xs text-text-tertiary">Deals Won</p>
          </Card>
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{c.import_volume_annual ? `${formatNumber(c.import_volume_annual)} MT` : "—"}</p>
            <p className="text-xs text-text-tertiary">Annual Volume</p>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Basic Info */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Basic Information</h3>
              <button onClick={() => openEdit("basic")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={MapPin} label="Location" value={[c.address, c.city, c.state, c.postal_code, c.country].filter(Boolean).join(", ") || null} />
              <InfoRow icon={Phone} label="Phone" value={c.phone} />
              <InfoRow icon={EnvelopeSimple} label="Email" value={c.email} href={c.email ? `mailto:${c.email}` : undefined} />
              <InfoRow icon={Globe} label="Website" value={c.website} href={c.website || undefined} />
              <InfoRow icon={Buildings} label="Industry" value={c.industry} />
            </div>
          </Card>

          {/* Business Profile */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Business Profile</h3>
              <button onClick={() => openEdit("business")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={Buildings} label="Company Type" value={c.company_type} />
              <InfoRow icon={Users} label="Employees" value={c.number_of_employees} />
              <InfoRow icon={Calendar} label="Year Established" value={c.year_established} />
              <InfoRow icon={CurrencyDollar} label="Annual Revenue" value={c.annual_revenue_usd ? `$${formatNumber(c.annual_revenue_usd)}` : null} />
              <InfoRow icon={IdentificationCard} label="Registration / License No." value={c.registration_number} />
              <InfoRow icon={IdentificationCard} label="Tax ID / VAT" value={c.tax_id} />
            </div>
          </Card>

          {/* Trade Intelligence */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Trade Intelligence</h3>
              <button onClick={() => openEdit("trade")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <TagList items={c.commodities} label="Commodities" />
            <TagList items={c.preferred_origins} label="Preferred Origins" />
            <div className="divide-y divide-border">
              <InfoRow icon={Scales} label="Incoterms" value={c.preferred_incoterms} />
              <InfoRow icon={CurrencyDollar} label="Payment Terms" value={c.preferred_payment_terms} />
              <InfoRow icon={Truck} label="Shipment Frequency" value={c.shipment_frequency} />
              <InfoRow icon={Calendar} label="Last Shipment" value={c.last_shipment_date} />
            </div>
            <TagList items={c.certifications_required} label="Certifications Required" />
            <TagList items={c.destination_ports} label="Destination Ports" />
          </Card>

          {/* Banking & Suppliers */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Banking & Suppliers</h3>
              <button onClick={() => openEdit("banking")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={Bank} label="Bank" value={[c.bank_name, c.bank_country].filter(Boolean).join(", ") || null} />
              <InfoRow icon={Bank} label="SWIFT / BIC" value={c.bank_swift_code} />
            </div>
            <TagList items={c.known_suppliers} label="Known Suppliers" />
          </Card>

          {/* Shipment Intelligence */}
          <Card className="lg:col-span-2 relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <Truck className="h-4 w-4 text-text-tertiary" /> Shipment Intelligence
              </h3>
              <div className="flex items-center gap-2">
                {shipmentSummary?.last_refreshed_at && (
                  <span className="text-[9px] text-text-tertiary">Updated {formatRelativeTime(shipmentSummary.last_refreshed_at)}</span>
                )}
                <button onClick={async () => { try { await api.post(`/companies/${id}/shipments/refresh`, {}); fetchCompany(); toast.success("Shipments refreshed"); } catch { toast.error("Refresh failed"); } }}
                  className="text-xs text-primary hover:underline cursor-pointer">Refresh</button>
              </div>
            </div>
            {!shipmentSummary || shipmentSummary.totals.total_shipments === 0 ? (
              <p className="text-xs text-text-tertiary py-3">No shipment records found for this company yet.</p>
            ) : (
              <>
                {/* Summary strip */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                  <div className="text-center p-2 rounded-[var(--radius-sm)] bg-border-light">
                    <p className="text-lg font-bold text-text-primary">{shipmentSummary.totals.shipments_12mo}</p>
                    <p className="text-[10px] text-text-tertiary">Shipments (12mo)</p>
                  </div>
                  <div className="text-center p-2 rounded-[var(--radius-sm)] bg-border-light">
                    <p className="text-lg font-bold text-text-primary">{formatNumber(shipmentSummary.totals.volume_12mo_mt)} MT</p>
                    <p className="text-[10px] text-text-tertiary">Volume (12mo)</p>
                  </div>
                  <div className="text-center p-2 rounded-[var(--radius-sm)] bg-border-light">
                    <p className="text-lg font-bold text-text-primary">{shipmentSummary.totals.avg_unit_price_usd_per_mt ? `$${formatNumber(shipmentSummary.totals.avg_unit_price_usd_per_mt)}` : "—"}</p>
                    <p className="text-[10px] text-text-tertiary">Avg Price/MT</p>
                  </div>
                  <div className="text-center p-2 rounded-[var(--radius-sm)] bg-border-light">
                    <p className="text-lg font-bold text-text-primary capitalize">{shipmentSummary.cadence || "—"}</p>
                    <p className="text-[10px] text-text-tertiary">Cadence</p>
                  </div>
                </div>

                {/* Top commodities */}
                {shipmentSummary.top_commodities.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wide mb-1.5">Top Commodities</p>
                    <div className="space-y-1.5">
                      {shipmentSummary.top_commodities.slice(0, 5).map((c, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <Package className="h-3 w-3 text-text-tertiary" />
                            <span className="text-text-primary font-medium">{c.name}</span>
                            {c.hs && <span className="text-text-tertiary">HS: {c.hs}</span>}
                          </div>
                          <div className="flex items-center gap-3 text-text-secondary">
                            <span>{c.shipments} shipments</span>
                            <span>{formatNumber(c.volume_mt)} MT</span>
                            {c.avg_price && <span>${formatNumber(c.avg_price)}/MT</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Top lanes */}
                {shipmentSummary.top_lanes.length > 0 && (
                  <div className="mb-3">
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wide mb-1.5">Trade Lanes</p>
                    <div className="space-y-1">
                      {shipmentSummary.top_lanes.slice(0, 3).map((l, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-1.5">
                            <Compass className="h-3 w-3 text-text-tertiary" />
                            <span className="text-text-primary">{l.origin_port} → {l.destination_port}</span>
                          </div>
                          <span className="text-text-secondary">{l.shipments} shipments · {formatNumber(l.volume_mt)} MT</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Role chip */}
                {shipmentSummary.role && (
                  <div className="pt-2 border-t border-border">
                    <span className="text-xs text-text-secondary">Role: </span>
                    <Badge size="sm" variant="outline" className="capitalize">{shipmentSummary.role.replace("_", "-")}</Badge>
                    <span className="text-[9px] text-text-tertiary ml-2">Powered by TradeCRM shipment data</span>
                  </div>
                )}
              </>
            )}
          </Card>

          {/* Trade Interests */}
          <Card className="lg:col-span-2 relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <Package className="h-4 w-4 text-text-tertiary" /> Trade Interests ({interests.filter((i) => i.status !== "rejected").length})
              </h3>
              <div className="flex items-center gap-2">
                <button onClick={async () => {
                  setInferring(true);
                  try { await api.post(`/interests/infer/${id}`, {}); fetchCompany(); toast.success("Interests updated"); }
                  catch { toast.error("Inference failed"); }
                  setInferring(false);
                }} disabled={inferring}
                  className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1 disabled:opacity-50">
                  <Sparkle className="h-3 w-3" /> {inferring ? "Analyzing..." : "Refresh from AI"}
                </button>
              </div>
            </div>
            {interests.filter((i) => i.status !== "rejected").length === 0 ? (
              <p className="text-xs text-text-tertiary py-2">No trade interests mapped yet. Click &quot;Refresh from AI&quot; to discover what this company trades.</p>
            ) : (
              <div className="space-y-2">
                {/* Confirmed first, then suggested */}
                {interests.filter((i) => i.status === "confirmed").map((i) => (
                  <div key={i.id} className="flex items-center justify-between p-2 rounded-[var(--radius-sm)] border border-border">
                    <div className="flex items-center gap-2">
                      <SealCheck className="h-4 w-4 text-success" />
                      <div>
                        <span className="text-sm font-medium text-text-primary">{i.product_name}</span>
                        {i.variety_name && <span className="text-xs text-text-secondary ml-1">· {i.variety_name}</span>}
                        {i.grade_name && <span className="text-xs text-text-tertiary ml-1">· {i.grade_name}</span>}
                        {(i.origin_port_name || i.destination_port_name) && (
                          <p className="text-[10px] text-text-tertiary">
                            {i.origin_port_name || "Any"} → {i.destination_port_name || "Any"}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                        i.confidence_level === "high" ? "bg-success/10 text-success" : i.confidence_level === "medium" ? "bg-warning/10 text-warning" : "bg-border text-text-tertiary"
                      }`}>{i.confidence_level}</span>
                      <Badge size="sm" variant="outline">{i.source.replace("_", " ")}</Badge>
                    </div>
                  </div>
                ))}
                {interests.filter((i) => i.status === "suggested").map((i) => (
                  <div key={i.id} className="flex items-center justify-between p-2 rounded-[var(--radius-sm)] border border-dashed border-border bg-border-light/30">
                    <div className="flex items-center gap-2">
                      <CircleDashed className="h-4 w-4 text-text-tertiary" />
                      <div>
                        <span className="text-sm text-text-secondary">{i.product_name}</span>
                        {(i.origin_port_name || i.destination_port_name) && (
                          <p className="text-[10px] text-text-tertiary">{i.origin_port_name || "Any"} → {i.destination_port_name || "Any"}</p>
                        )}
                        {i.evidence && (i.evidence as Record<string, string>).explanation && (
                          <p className="text-[10px] text-text-tertiary italic">{(i.evidence as Record<string, string>).explanation}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                        i.confidence_level === "high" ? "bg-success/10 text-success" : i.confidence_level === "medium" ? "bg-warning/10 text-warning" : "bg-border text-text-tertiary"
                      }`}>{i.confidence_level}</span>
                      <button onClick={async () => { try { await api.post("/interests/bulk-accept", { interest_ids: [i.id] }); fetchCompany(); toast.success("Accepted"); } catch { toast.error("Failed"); } }}
                        className="px-2 py-0.5 text-[10px] font-medium text-success bg-success/10 rounded hover:bg-success/20 cursor-pointer">Accept</button>
                      <button onClick={async () => { try { await api.post("/interests/bulk-reject", { interest_ids: [i.id] }); fetchCompany(); toast.success("Dismissed"); } catch { toast.error("Failed"); } }}
                        className="px-2 py-0.5 text-[10px] font-medium text-text-tertiary bg-border rounded hover:bg-border-light cursor-pointer">Dismiss</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Linked Opportunities */}
          <Card className="lg:col-span-2 relative" id="linked-opps">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <Kanban className="h-4 w-4 text-text-tertiary" /> Opportunities ({opportunities.length})
              </h3>
              <button onClick={() => router.push("/opportunities")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                View All <ArrowRight className="h-3 w-3" />
              </button>
            </div>
            {opportunities.length === 0 ? (
              <p className="text-xs text-text-tertiary py-2">No active opportunities for this company</p>
            ) : (
              <div className="space-y-2">
                {opportunities.map((opp) => (
                  <div key={opp.id} onClick={() => router.push(`/opportunities/${opp.id}`)}
                    className="flex items-center justify-between p-2.5 rounded-[var(--radius-sm)] border border-border hover:bg-border-light transition-colors cursor-pointer">
                    <div className="flex items-center gap-3 min-w-0">
                      {opp.stage_color && <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: opp.stage_color }} />}
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">{opp.title || "Untitled"}</p>
                        <p className="text-xs text-text-secondary">{[opp.commodity, opp.quantity_mt ? `${opp.quantity_mt} MT` : null].filter(Boolean).join(" · ")}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {opp.display_id && <span className="text-[10px] font-mono text-text-tertiary">{opp.display_id}</span>}
                      <Badge size="sm" variant="outline">{opp.stage_name}</Badge>
                      {opp.estimated_value_usd && <span className="text-xs font-medium text-primary">${formatNumber(opp.estimated_value_usd)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Linked Leads */}
          <Card className="lg:col-span-2 relative" id="linked-leads">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <UserFocus className="h-4 w-4 text-text-tertiary" /> Leads ({leads.length})
              </h3>
              <button onClick={() => router.push("/leads")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                View All <ArrowRight className="h-3 w-3" />
              </button>
            </div>
            {leads.length === 0 ? (
              <p className="text-xs text-text-tertiary py-2">No leads from this company</p>
            ) : (
              <div className="space-y-2">
                {leads.map((lead) => (
                  <div key={lead.id} onClick={() => router.push(`/leads?search=${encodeURIComponent(lead.sender_company || "")}`)}
                    className="flex items-center justify-between p-2.5 rounded-[var(--radius-sm)] border border-border hover:bg-border-light transition-colors cursor-pointer">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">{lead.subject || "(no subject)"}</p>
                      <p className="text-xs text-text-secondary">{lead.sender_name} · {lead.sender_email}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge size="sm" variant={lead.classification === "lead" ? "success" : "outline"}>{lead.classification}</Badge>
                      <Badge size="sm" variant="outline">{lead.status}</Badge>
                      <span className="text-[10px] text-text-tertiary">{lead.received_at ? formatRelativeTime(lead.received_at) : "—"}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Additional */}
          <Card className="lg:col-span-2 relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Additional</h3>
              <button onClick={() => openEdit("additional")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
              <div className="divide-y divide-border">
                <InfoRow icon={LinkedinLogo} label="LinkedIn" value={c.linkedin_url} href={c.linkedin_url || undefined} />
              </div>
              <div>
                <TagList items={c.tags} label="Tags" />
              </div>
            </div>
            {c.notes && (
              <div className="mt-3 pt-3 border-t border-border">
                <div className="flex items-start gap-3">
                  <Notebook className="h-4 w-4 text-text-tertiary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wide">Notes</p>
                    <p className="text-sm text-text-primary whitespace-pre-wrap">{c.notes}</p>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Edit Modal */}
        <Modal open={showEdit} onOpenChange={setShowEdit}
          title={`Edit ${editSection === "basic" ? "Basic Info" : editSection === "business" ? "Business Profile" : editSection === "trade" ? "Trade Intelligence" : editSection === "banking" ? "Banking & Suppliers" : "Additional"}`}
          size="md"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <Button variant="secondary" onClick={() => setShowEdit(false)}>Cancel</Button>
              <Button onClick={handleSave} isLoading={saving}>Save Changes</Button>
            </div>
          }
        >
          <div className="space-y-4">
            {editSection === "basic" && <>
              <Input label="Company Name" value={editData.name || ""} onChange={(e) => setEd("name", e.target.value)} />
              <Textarea label="Description" value={editData.description || ""} onChange={(e) => setEd("description", e.target.value)} rows={2} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Country" value={editData.country || ""} onChange={(e) => setEd("country", e.target.value)} />
                <Input label="City" value={editData.city || ""} onChange={(e) => setEd("city", e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="State / Province" value={editData.state || ""} onChange={(e) => setEd("state", e.target.value)} />
                <Input label="Postal Code" value={editData.postal_code || ""} onChange={(e) => setEd("postal_code", e.target.value)} />
              </div>
              <Input label="Address" value={editData.address || ""} onChange={(e) => setEd("address", e.target.value)} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Phone" value={editData.phone || ""} onChange={(e) => setEd("phone", e.target.value)} />
                <Input label="Email" value={editData.email || ""} onChange={(e) => setEd("email", e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Website" value={editData.website || ""} onChange={(e) => setEd("website", e.target.value)} />
                <Input label="Industry" value={editData.industry || ""} onChange={(e) => setEd("industry", e.target.value)} />
              </div>
            </>}

            {editSection === "business" && <>
              <ChipSelect field="company_type" label="Company Type" options={COMPANY_TYPES} />
              <ChipSelect field="company_size" label="Company Size" options={["small", "medium", "large", "enterprise"]} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Year Established" type="number" value={editData.year_established || ""} onChange={(e) => setEd("year_established", e.target.value)} />
                <ChipSelect field="number_of_employees" label="Employees" options={EMPLOYEE_RANGES} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Annual Revenue (USD)" type="number" value={editData.annual_revenue_usd || ""} onChange={(e) => setEd("annual_revenue_usd", e.target.value)} />
                <Input label="Registration / License No." value={editData.registration_number || ""} onChange={(e) => setEd("registration_number", e.target.value)} />
              </div>
              <Input label="Tax ID / VAT" value={editData.tax_id || ""} onChange={(e) => setEd("tax_id", e.target.value)} />
              <div>
                <p className="text-[13px] font-medium text-text-primary mb-1.5">Rating</p>
                <div className="flex gap-2">
                  {["hot", "warm", "cold"].map((v) => (
                    <button key={v} onClick={() => setEd("rating", editData.rating === v ? "" : v)}
                      className={`px-3 py-1.5 rounded-[var(--radius-full)] text-xs border transition-colors cursor-pointer capitalize ${
                        editData.rating === v ? (v === "hot" ? "bg-error/10 text-red-700 border-error/30" : v === "warm" ? "bg-warning/10 text-amber-700 border-warning/30" : "bg-info/10 text-blue-700 border-info/30") : "bg-surface text-text-secondary border-border"
                      }`}>{v}</button>
                  ))}
                </div>
              </div>
            </>}

            {editSection === "trade" && <>
              <ProductPicker label="Commodities" value={editCommodities} onChange={setEditCommodities} multi placeholder="Search your catalog..." />
              <Input label="Preferred Origins (comma-separated)" value={editData.preferred_origins || ""} onChange={(e) => setEd("preferred_origins", e.target.value)} />
              <div className="grid grid-cols-2 gap-4">
                <ChipSelect field="preferred_incoterms" label="Preferred Incoterms" options={INCOTERMS} />
                <ChipSelect field="preferred_payment_terms" label="Payment Terms" options={PAYMENT_TERMS} />
              </div>
              <Input label="Certifications Required (comma-separated)" value={editData.certifications_required || ""} onChange={(e) => setEd("certifications_required", e.target.value)} />
              <Input label="Destination Ports (comma-separated)" value={editData.destination_ports || ""} onChange={(e) => setEd("destination_ports", e.target.value)} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Annual Import Volume (MT)" type="number" value={editData.import_volume_annual || ""} onChange={(e) => setEd("import_volume_annual", e.target.value)} />
                <ChipSelect field="shipment_frequency" label="Shipment Frequency" options={SHIPMENT_FREQ} />
              </div>
            </>}

            {editSection === "banking" && <>
              <Input label="Bank Name" value={editData.bank_name || ""} onChange={(e) => setEd("bank_name", e.target.value)} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Bank Country" value={editData.bank_country || ""} onChange={(e) => setEd("bank_country", e.target.value)} />
                <Input label="SWIFT / BIC Code" value={editData.bank_swift_code || ""} onChange={(e) => setEd("bank_swift_code", e.target.value)} />
              </div>
              <Input label="Known Suppliers (comma-separated)" value={editData.known_suppliers || ""} onChange={(e) => setEd("known_suppliers", e.target.value)} />
            </>}

            {editSection === "additional" && <>
              <Input label="LinkedIn URL" value={editData.linkedin_url || ""} onChange={(e) => setEd("linkedin_url", e.target.value)} />
              <Input label="Tags (comma-separated)" value={editData.tags || ""} onChange={(e) => setEd("tags", e.target.value)} />
              <Textarea label="Notes" value={editData.notes || ""} onChange={(e) => setEd("notes", e.target.value)} rows={4} />
            </>}
          </div>
        </Modal>

        {/* Enrichment Panel */}
        {showEnrichPanel && enrichTaskId && (
          <EnrichmentPanel
            companyId={id}
            companyName={c.name}
            agentTaskId={enrichTaskId}
            enrichmentsRemaining={enrichmentsRemaining}
            onClose={() => setShowEnrichPanel(false)}
            onComplete={handleEnrichComplete}
          />
        )}
      </FullWidthLayout>
    </AppShell>
  );
}
