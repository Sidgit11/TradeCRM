"use client";
import type { Contact, PipelineOpportunity, InboundLead, InsightsResponse, InsightItem } from "@/types";

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
  ArrowLeft, PencilSimple, User, MapPin, Phone,
  EnvelopeSimple, Buildings, WhatsappLogo, LinkedinLogo,
  ChatCircle, Notebook, ProhibitInset, Star,
  ArrowsClockwise, Globe, Kanban, UserFocus, ArrowRight, Sparkle,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime, formatNumber } from "@/lib/utils";


const SALUTATIONS = ["Mr", "Mrs", "Ms", "Dr", "Prof"];
const DEPARTMENTS = ["Procurement", "Trading", "Management", "Operations", "Quality", "Logistics", "Finance", "Other"];

function InfoRow({ icon: Icon, label, value, href, badge }: { icon: React.ElementType; label: string; value: string | number | null | undefined; href?: string; badge?: boolean }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="h-4 w-4 text-text-tertiary mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-[11px] text-text-tertiary uppercase tracking-wide">{label}</p>
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline break-all">{String(value)}</a>
        ) : badge ? (
          <Badge size="sm">{String(value)}</Badge>
        ) : (
          <p className="text-sm text-text-primary break-all">{String(value)}</p>
        )}
      </div>
    </div>
  );
}

export default function ContactDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [showEdit, setShowEdit] = useState(false);
  const [editSection, setEditSection] = useState("");
  const [saving, setSaving] = useState(false);
  const [editData, setEditData] = useState<Record<string, string | boolean>>({});
  const [opportunities, setOpportunities] = useState<PipelineOpportunity[]>([]);
  const [leads, setLeads] = useState<InboundLead[]>([]);
  const [insights, setInsights] = useState<InsightItem[]>([]);

  const fetchContact = useCallback(async () => {
    setLoading(true);
    try {
      const [contactRes, oppsRes, leadsRes] = await Promise.all([
        api.get<Contact>(`/contacts/${id}`),
        api.get<PipelineOpportunity[]>(`/pipeline?contact_id=${id}&active_only=true`),
        api.get<{ items: InboundLead[] }>(`/leads?tab=all&contact_id=${id}&active_only=true&limit=20`),
      ]);
      setContact(contactRes.data);
      setOpportunities(oppsRes.data);
      setLeads(leadsRes.data.items || []);
    } catch { toast.error("Failed to load contact"); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchContact(); }, [fetchContact]);
  useEffect(() => { if (id) api.get<InsightsResponse>(`/insights/contact/${id}`).then(({ data }) => setInsights(data.insights || [])).catch(() => {}); }, [id]);

  const openEdit = (section: string) => {
    if (!contact) return;
    const c = contact;
    const data: Record<string, string | boolean> = {};

    if (section === "contact") {
      data.salutation = c.salutation || ""; data.name = c.name || "";
      data.email = c.email || ""; data.secondary_email = c.secondary_email || "";
      data.phone = c.phone || ""; data.secondary_phone = c.secondary_phone || "";
      data.whatsapp_number = c.whatsapp_number || "";
    } else if (section === "location") {
      data.country = c.country || ""; data.city = c.city || "";
      data.company_name = c.company_name || "";
      data.title = c.title || ""; data.department = c.department || "";
      data.is_decision_maker = c.is_decision_maker;
    } else if (section === "preferences") {
      data.preferred_channel = c.preferred_channel || "";
      data.preferred_language = c.preferred_language || "";
      data.do_not_contact = c.do_not_contact;
      data.opted_in_whatsapp = c.opted_in_whatsapp;
      data.opted_in_email = c.opted_in_email;
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
      const payload: Record<string, unknown> = {};

      if (editSection === "contact") {
        Object.assign(payload, {
          salutation: (editData.salutation as string)?.trim() || null,
          name: (editData.name as string)?.trim(),
          email: (editData.email as string)?.trim() || null,
          secondary_email: (editData.secondary_email as string)?.trim() || null,
          phone: (editData.phone as string)?.trim() || null,
          secondary_phone: (editData.secondary_phone as string)?.trim() || null,
          whatsapp_number: (editData.whatsapp_number as string)?.trim() || null,
        });
      } else if (editSection === "location") {
        Object.assign(payload, {
          country: (editData.country as string)?.trim() || null,
          city: (editData.city as string)?.trim() || null,
          company_name: (editData.company_name as string)?.trim() || null,
          title: (editData.title as string)?.trim() || null,
          department: (editData.department as string)?.trim() || null,
          is_decision_maker: editData.is_decision_maker,
        });
      } else if (editSection === "preferences") {
        Object.assign(payload, {
          preferred_channel: (editData.preferred_channel as string) || null,
          preferred_language: (editData.preferred_language as string)?.trim() || null,
          do_not_contact: editData.do_not_contact,
          opted_in_whatsapp: editData.opted_in_whatsapp,
          opted_in_email: editData.opted_in_email,
        });
      } else if (editSection === "additional") {
        const csvToArr = (s: string) => s ? s.split(",").map((v) => v.trim()).filter(Boolean) : [];
        Object.assign(payload, {
          linkedin_url: (editData.linkedin_url as string)?.trim() || null,
          tags: csvToArr(editData.tags as string || ""),
          notes: (editData.notes as string)?.trim() || null,
        });
      }

      await api.put(`/contacts/${id}`, payload);
      toast.success("Contact updated");
      setShowEdit(false);
      fetchContact();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to update contact")); }
    setSaving(false);
  };

  const setEd = (k: string, v: string | boolean) => setEditData((d) => ({ ...d, [k]: v }));

  const Toggle = ({ field, label, sublabel }: { field: string; label: string; sublabel?: string }) => (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-text-primary">{label}</p>
        {sublabel && <p className="text-xs text-text-secondary">{sublabel}</p>}
      </div>
      <button onClick={() => setEd(field, !editData[field])}
        className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${editData[field] ? "bg-primary" : "bg-border"}`}>
        <div className={`w-5 h-5 rounded-full bg-surface shadow-sm transition-transform ${editData[field] ? "translate-x-5.5" : "translate-x-0.5"}`} />
      </button>
    </div>
  );

  if (loading) {
    return <AppShell title="Contact"><FullWidthLayout><Skeleton variant="card" className="h-32 mb-4" /><Skeleton variant="card" className="h-48" /></FullWidthLayout></AppShell>;
  }

  if (!contact) {
    return <AppShell title="Contact"><FullWidthLayout><p className="text-sm text-text-secondary">Contact not found</p></FullWidthLayout></AppShell>;
  }

  const c = contact;
  const displayName = `${c.salutation ? c.salutation + ". " : ""}${c.name}`;

  return (
    <AppShell title={c.name}>
      <FullWidthLayout>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/contacts")} className="text-text-tertiary hover:text-text-primary cursor-pointer">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                {c.do_not_contact && <ProhibitInset className="h-5 w-5 text-error" weight="fill" />}
                <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{displayName}</h2>
                {c.is_decision_maker && <Badge variant="success" size="md">Decision Maker</Badge>}
              </div>
              <div className="flex items-center gap-3 mt-0.5">
                {c.title && <span className="text-sm text-text-secondary">{c.title}</span>}
                {c.company_name && (
                  <span className="text-sm text-text-secondary flex items-center gap-1">
                    <Buildings className="h-3.5 w-3.5" />
                    {c.company_id ? (
                      <a href={`/companies/${c.company_id}`} className="text-primary hover:underline">{c.company_name}</a>
                    ) : c.company_name}
                  </span>
                )}
              </div>
              <p className="text-xs text-text-tertiary mt-0.5">
                Added {formatRelativeTime(c.created_at)} via {c.source}
                {c.last_interaction_at && ` / Last interaction ${formatRelativeTime(c.last_interaction_at)}`}
                {c.last_contacted_at && ` / Last contacted ${formatRelativeTime(c.last_contacted_at)}`}
              </p>
            </div>
          </div>
          <Button variant="ghost" onClick={fetchContact}><ArrowsClockwise className="h-4 w-4 mr-1" /> Refresh</Button>
        </div>

        {/* AI Insights */}
        {insights.length > 0 && (
          <div className="mb-6 space-y-2">
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide flex items-center gap-1">
              <Sparkle className="h-3.5 w-3.5 text-warning" /> AI Insights
            </h3>
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

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Card className="p-3 text-center cursor-pointer hover:shadow-[var(--shadow-md)] transition-shadow" onClick={() => opportunities.length > 0 && document.getElementById("contact-opps")?.scrollIntoView({ behavior: "smooth" })}>
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-primary">{opportunities.length}</p>
            <p className="text-xs text-text-tertiary">Opportunities</p>
          </Card>
          <Card className="p-3 text-center cursor-pointer hover:shadow-[var(--shadow-md)] transition-shadow" onClick={() => leads.length > 0 && document.getElementById("contact-leads")?.scrollIntoView({ behavior: "smooth" })}>
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{leads.length}</p>
            <p className="text-xs text-text-tertiary">Leads</p>
          </Card>
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{c.total_interactions}</p>
            <p className="text-xs text-text-tertiary">Interactions</p>
          </Card>
          <Card className="p-3 text-center">
            <p className={`text-2xl font-bold font-[family-name:var(--font-heading)] ${c.do_not_contact ? "text-error" : "text-success"}`}>
              {c.do_not_contact ? "DNC" : "Active"}
            </p>
            <p className="text-xs text-text-tertiary">Status</p>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Contact Info */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Contact Information</h3>
              <button onClick={() => openEdit("contact")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={EnvelopeSimple} label="Email" value={c.email} href={c.email ? `mailto:${c.email}` : undefined} />
              {c.secondary_email && <InfoRow icon={EnvelopeSimple} label="Secondary Email" value={c.secondary_email} href={`mailto:${c.secondary_email}`} />}
              <InfoRow icon={Phone} label="Phone" value={c.phone} />
              {c.secondary_phone && <InfoRow icon={Phone} label="Secondary Phone" value={c.secondary_phone} />}
              <InfoRow icon={WhatsappLogo} label="WhatsApp" value={c.whatsapp_number || c.phone} href={c.whatsapp_number || c.phone ? `https://wa.me/${(c.whatsapp_number || c.phone || "").replace(/[^0-9]/g, "")}` : undefined} />
            </div>
          </Card>

          {/* Location & Company */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Professional Details</h3>
              <button onClick={() => openEdit("location")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={Buildings} label="Company" value={c.company_name} />
              <InfoRow icon={User} label="Title / Designation" value={c.title} />
              <InfoRow icon={User} label="Department" value={c.department} />
              <InfoRow icon={MapPin} label="Location" value={[c.city, c.country].filter(Boolean).join(", ") || null} />
              {c.is_decision_maker && (
                <div className="flex items-start gap-3 py-2">
                  <Star className="h-4 w-4 text-warning mt-0.5 shrink-0" weight="fill" />
                  <div>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wide">Role</p>
                    <p className="text-sm text-text-primary">Key Decision Maker</p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Communication Preferences */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Communication Preferences</h3>
              <button onClick={() => openEdit("preferences")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={ChatCircle} label="Preferred Channel" value={c.preferred_channel} badge />
              <InfoRow icon={Globe} label="Preferred Language" value={c.preferred_language} />
              <div className="flex items-start gap-3 py-2">
                <EnvelopeSimple className="h-4 w-4 text-text-tertiary mt-0.5 shrink-0" />
                <div>
                  <p className="text-[11px] text-text-tertiary uppercase tracking-wide">Consent</p>
                  <div className="flex gap-2 mt-1">
                    <Badge size="sm" variant={c.opted_in_email ? "success" : "default"}>Email {c.opted_in_email ? "Opted In" : "Opted Out"}</Badge>
                    <Badge size="sm" variant={c.opted_in_whatsapp ? "success" : "default"}>WhatsApp {c.opted_in_whatsapp ? "Opted In" : "Opted Out"}</Badge>
                  </div>
                </div>
              </div>
              {c.do_not_contact && (
                <div className="flex items-start gap-3 py-2">
                  <ProhibitInset className="h-4 w-4 text-error mt-0.5 shrink-0" weight="fill" />
                  <div>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wide">Do Not Contact</p>
                    <p className="text-sm text-error font-medium">This contact has opted out of all outreach</p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Linked Opportunities */}
          <Card className="lg:col-span-2 relative" id="contact-opps">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <Kanban className="h-4 w-4 text-text-tertiary" /> Opportunities ({opportunities.length})
              </h3>
              <button onClick={() => router.push("/opportunities")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                View All <ArrowRight className="h-3 w-3" />
              </button>
            </div>
            {opportunities.length === 0 ? (
              <p className="text-xs text-text-tertiary py-2">No opportunities linked to this contact</p>
            ) : (
              <div className="space-y-2">
                {opportunities.map((opp) => (
                  <div key={opp.id} onClick={() => router.push(`/opportunities/${opp.id}`)}
                    className="flex items-center justify-between p-2.5 rounded-[var(--radius-sm)] border border-border hover:bg-border-light transition-colors cursor-pointer">
                    <div className="flex items-center gap-3 min-w-0">
                      {opp.stage_color && <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: opp.stage_color }} />}
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">{opp.title || "Untitled"}</p>
                        <p className="text-xs text-text-secondary">{[opp.company_name, opp.commodity, opp.quantity_mt ? `${opp.quantity_mt} MT` : null].filter(Boolean).join(" · ")}</p>
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
          <Card className="lg:col-span-2 relative" id="contact-leads">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <UserFocus className="h-4 w-4 text-text-tertiary" /> Leads ({leads.length})
              </h3>
              <button onClick={() => router.push("/leads")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                View All <ArrowRight className="h-3 w-3" />
              </button>
            </div>
            {leads.length === 0 ? (
              <p className="text-xs text-text-tertiary py-2">No leads linked to this contact</p>
            ) : (
              <div className="space-y-2">
                {leads.map((lead) => (
                  <div key={lead.id} onClick={() => router.push(`/leads`)}
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
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Additional</h3>
              <button onClick={() => openEdit("additional")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={LinkedinLogo} label="LinkedIn" value={c.linkedin_url} href={c.linkedin_url || undefined} />
            </div>
            {c.tags.length > 0 && (
              <div className="py-2">
                <p className="text-[11px] text-text-tertiary uppercase tracking-wide mb-1.5">Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {c.tags.map((tag) => <Badge key={tag} size="sm">{tag}</Badge>)}
                </div>
              </div>
            )}
            {c.notes && (
              <div className="mt-2 pt-2 border-t border-border">
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
          title={`Edit ${editSection === "contact" ? "Contact Info" : editSection === "location" ? "Professional Details" : editSection === "preferences" ? "Preferences" : "Additional"}`}
          size="md"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <Button variant="secondary" onClick={() => setShowEdit(false)}>Cancel</Button>
              <Button onClick={handleSave} isLoading={saving}>Save Changes</Button>
            </div>
          }
        >
          <div className="space-y-4">
            {editSection === "contact" && <>
              <div className="flex gap-3">
                <div className="w-28">
                  <p className="text-[13px] font-medium text-text-primary mb-1.5">Salutation</p>
                  <div className="flex flex-wrap gap-1">
                    {SALUTATIONS.map((s) => (
                      <button key={s} onClick={() => setEd("salutation", editData.salutation === s ? "" : s)}
                        className={`px-2 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                          editData.salutation === s ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                        }`}>{s}</button>
                    ))}
                  </div>
                </div>
                <div className="flex-1">
                  <Input label="Full Name" value={editData.name as string || ""} onChange={(e) => setEd("name", e.target.value)} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Email" value={editData.email as string || ""} onChange={(e) => setEd("email", e.target.value)} />
                <Input label="Secondary Email" value={editData.secondary_email as string || ""} onChange={(e) => setEd("secondary_email", e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Phone" value={editData.phone as string || ""} onChange={(e) => setEd("phone", e.target.value)} />
                <Input label="Secondary Phone" value={editData.secondary_phone as string || ""} onChange={(e) => setEd("secondary_phone", e.target.value)} />
              </div>
              <Input label="WhatsApp Number" value={editData.whatsapp_number as string || ""} onChange={(e) => setEd("whatsapp_number", e.target.value)} helperText="Leave blank if same as phone" />
            </>}

            {editSection === "location" && <>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Country" value={editData.country as string || ""} onChange={(e) => setEd("country", e.target.value)} />
                <Input label="City" value={editData.city as string || ""} onChange={(e) => setEd("city", e.target.value)} />
              </div>
              <Input label="Company" value={editData.company_name as string || ""} onChange={(e) => setEd("company_name", e.target.value)} />
              <Input label="Title / Designation" value={editData.title as string || ""} onChange={(e) => setEd("title", e.target.value)} />
              <div>
                <p className="text-[13px] font-medium text-text-primary mb-1.5">Department</p>
                <div className="flex flex-wrap gap-1.5">
                  {DEPARTMENTS.map((d) => (
                    <button key={d} onClick={() => setEd("department", editData.department === d ? "" : d)}
                      className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                        editData.department === d ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                      }`}>{d}</button>
                  ))}
                </div>
              </div>
              <Toggle field="is_decision_maker" label="Decision Maker" sublabel="Is this person a key decision maker?" />
            </>}

            {editSection === "preferences" && <>
              <div>
                <p className="text-[13px] font-medium text-text-primary mb-1.5">Preferred Channel</p>
                <div className="flex gap-2">
                  {["email", "whatsapp", "phone"].map((v) => (
                    <button key={v} onClick={() => setEd("preferred_channel", editData.preferred_channel === v ? "" : v)}
                      className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer capitalize ${
                        editData.preferred_channel === v ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                      }`}>{v === "whatsapp" ? "WhatsApp" : v.charAt(0).toUpperCase() + v.slice(1)}</button>
                  ))}
                </div>
              </div>
              <Input label="Preferred Language" placeholder="e.g. en, de, es" value={editData.preferred_language as string || ""} onChange={(e) => setEd("preferred_language", e.target.value)} />
              <Toggle field="do_not_contact" label="Do Not Contact" sublabel="Opt out of all outreach" />
              <Toggle field="opted_in_email" label="Email Opt-in" sublabel="Consent to receive emails" />
              <Toggle field="opted_in_whatsapp" label="WhatsApp Opt-in" sublabel="Consent to receive WhatsApp messages" />
            </>}

            {editSection === "additional" && <>
              <Input label="LinkedIn URL" value={editData.linkedin_url as string || ""} onChange={(e) => setEd("linkedin_url", e.target.value)} />
              <Input label="Tags (comma-separated)" value={editData.tags as string || ""} onChange={(e) => setEd("tags", e.target.value)} />
              <Textarea label="Notes" value={editData.notes as string || ""} onChange={(e) => setEd("notes", e.target.value)} rows={4} />
            </>}
          </div>
        </Modal>
      </FullWidthLayout>
    </AppShell>
  );
}
