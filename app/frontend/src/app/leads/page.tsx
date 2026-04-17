"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  ArrowsClockwise, UserFocus, Star, EnvelopeSimple, WhatsappLogo,
  Phone, Buildings, MapPin, Package, CaretRight,
  Check, X, PencilSimple, UserPlus, Kanban, PaperPlaneTilt,
  Warning, Eye, FunnelSimple, MagnifyingGlass,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime, truncate } from "@/lib/utils";

interface Lead {
  id: string;
  classification: string;
  non_lead_reason: string | null;
  confidence: number | null;
  sender_name: string | null;
  sender_email: string;
  sender_phone: string | null;
  sender_company: string | null;
  sender_designation: string | null;
  matched_contact_id: string | null;
  matched_company_id: string | null;
  subject: string | null;
  body_preview: string | null;
  body_full?: string | null;
  received_at: string;
  thread_message_count: number;
  products_mentioned: Array<{ raw: string; matched_product_name?: string; matched_grade_name?: string; confidence: number }>;
  quantities: Array<{ raw: string; value?: number; unit?: string }>;
  target_price: string | null;
  delivery_terms: string | null;
  destination: string | null;
  urgency: string | null;
  specific_questions: string | null;
  status: string;
  is_high_value: boolean;
  assigned_to: string | null;
  contact_id: string | null;
  company_id: string | null;
  notes: string | null;
  draft_reply: string | null;
  draft_reply_explanation: string | null;
  created_at: string;
}

interface LeadStats {
  leads: number;
  other: number;
  new: number;
  total: number;
}

interface EmailAccount {
  id: string;
  email_address: string;
}

const URGENCY_BADGE: Record<string, { label: string; variant: "success" | "warning" | "error" }> = {
  immediate: { label: "Urgent", variant: "error" },
  this_month: { label: "This Month", variant: "warning" },
  exploring: { label: "Exploring", variant: "default" as "success" },
};

const NON_LEAD_LABELS: Record<string, string> = {
  newsletter: "Newsletter",
  notification: "Notification",
  vendor_pitch: "Vendor Pitch",
  job_application: "Job Application",
  personal: "Personal",
  product_not_in_catalog: "Product Not in Catalog",
  below_min_qty: "Below Min Qty",
  blocked_country: "Blocked Country",
  spam: "Spam",
  other: "Other",
};

export default function LeadsPage() {
  const [tab, setTab] = useState<"leads" | "other">("leads");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<LeadStats>({ leads: 0, other: 0, new: 0, total: 0 });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [sortBy, setSortBy] = useState("created_at");
  const [search, setSearch] = useState("");

  // Draft reply
  const [showReplyBar, setShowReplyBar] = useState(false);
  const [replyChannel, setReplyChannel] = useState<"email" | "whatsapp">("email");
  const [replyInstruction, setReplyInstruction] = useState("");
  const [draftReply, setDraftReply] = useState<{ subject: string; draft: string; explanation: string } | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [editedReply, setEditedReply] = useState("");
  const [sending, setSending] = useState(false);

  // Save to CRM result
  const [crmResult, setCrmResult] = useState<{ contact_id: string; company_id: string | null } | null>(null);

  const fetchLeads = useCallback(async () => {
    try {
      const [leadsRes, statsRes] = await Promise.all([
        api.get<{ items: Lead[]; total: number }>(`/leads?tab=${tab}&limit=50&sort_by=${sortBy}${search ? `&search=${encodeURIComponent(search)}` : ""}${statusFilter ? `&status=${statusFilter}` : ""}`),
        api.get<LeadStats>("/leads/stats"),
      ]);
      setLeads(leadsRes.data.items);
      setStats(statsRes.data);
    } catch { toast.error("Failed to load data"); }
    setLoading(false);
  }, [tab, search, statusFilter, sortBy]);

  const fetchAccounts = useCallback(async () => {
    try {
      const { data } = await api.get<EmailAccount[]>("/email/accounts");
      setAccounts(data);
    } catch { toast.error("Failed to load data"); }
  }, []);

  useEffect(() => { fetchLeads(); fetchAccounts(); }, [fetchLeads, fetchAccounts]);

  const handleSync = async () => {
    if (accounts.length === 0) { toast.error("No email accounts connected. Go to Settings > Integrations."); return; }
    setSyncing(true);
    try {
      let totalLeads = 0;
      let totalNonLeads = 0;
      for (const acct of accounts) {
        const { data } = await api.post<{ leads: number; non_leads: number; skipped: number }>(`/leads/sync/${acct.id}`);
        totalLeads += data.leads;
        totalNonLeads += data.non_leads;
      }
      toast.success(`Sync complete: ${totalLeads} leads, ${totalNonLeads} other`);
      fetchLeads();
    } catch (err) { toast.error(getErrorMessage(err, "Sync failed")); }
    setSyncing(false);
  };

  const handleDismiss = async (leadId: string) => {
    try {
      await api.post(`/leads/${leadId}/dismiss`);
      toast.success("Lead dismissed");
      setSelectedLead(null);
      fetchLeads();
    } catch (err) { toast.error(getErrorMessage(err, "Action failed")); }
  };

  const handleMoveToPipeline = async (leadId: string) => {
    try {
      const { data } = await api.post<{ contact_id: string; company_id: string | null; opportunity_id: string | null }>(
        `/leads/${leadId}/move-to-pipeline`
      );
      toast.success("Moved to Pipeline — Contact, Company, and Opportunity created");
      fetchLeads();
      if (selectedLead) {
        const { data: updated } = await api.get<Lead>(`/leads/${leadId}`);
        setSelectedLead(updated);
      }
    } catch (err) { toast.error(getErrorMessage(err, "Failed to move to pipeline")); }
  };

  const handleMarkAsLead = async (leadId: string) => {
    try {
      await api.put(`/leads/${leadId}`, { classification: "lead", non_lead_reason: null });
      toast.success("Marked as lead");
      fetchLeads();
    } catch (err) { toast.error(getErrorMessage(err, "Action failed")); }
  };

  const handleMarkAsNonLead = async (leadId: string) => {
    try {
      await api.put(`/leads/${leadId}`, { classification: "non_lead", non_lead_reason: "other" });
      toast.success("Moved to Other");
      setSelectedLead(null);
      fetchLeads();
    } catch (err) { toast.error(getErrorMessage(err, "Action failed")); }
  };

  const handleDraftReply = async (leadId: string) => {
    if (!replyInstruction.trim()) { toast.error("Tell the AI how to reply, e.g. 'Send them the quotation'"); return; }
    setDrafting(true);
    setDraftReply(null);
    try {
      const { data } = await api.post<{ subject: string; draft: string; explanation: string }>(
        `/leads/${leadId}/draft-reply`,
        { user_instruction: replyInstruction.trim(), channel: replyChannel },
      );
      setDraftReply(data);
      setEditedReply(data.draft);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to generate draft reply")); }
    setDrafting(false);
  };

  const handleSendReply = async (leadId: string) => {
    if (!editedReply.trim()) return;
    setSending(true);
    try {
      await api.post(`/leads/${leadId}/send-reply`, {
        body_html: editedReply.replace(/\n/g, "<br>"),
        subject: draftReply?.subject || `Re: ${selectedLead?.subject || ""}`,
      });
      toast.success("Reply sent via Gmail");
      setShowReplyBar(false);
      setDraftReply(null);
      setReplyInstruction("");
      setEditedReply("");
      fetchLeads();
      if (selectedLead) {
        const { data: updated } = await api.get<Lead>(`/leads/${leadId}`);
        setSelectedLead(updated);
      }
    } catch (err) { toast.error(getErrorMessage(err, "Failed to send reply")); }
    setSending(false);
  };

  const openDetail = async (lead: Lead) => {
    try {
      const { data } = await api.get<Lead>(`/leads/${lead.id}`);
      setSelectedLead(data);
    } catch {
      toast.error("Failed to load lead details");
      setSelectedLead(lead);
    }
  };

  return (
    <AppShell title="Leads">
      <FullWidthLayout>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Inbound Leads</h2>
            <p className="text-sm text-text-secondary mt-0.5">Emails classified by AI from your connected accounts</p>
          </div>
          <Button onClick={handleSync} isLoading={syncing}>
            <ArrowsClockwise className="h-4 w-4 mr-1" /> Sync Now
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-4 border-b border-border mb-4">
          <button
            onClick={() => setTab("leads")}
            className={`pb-2.5 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              tab === "leads" ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            Leads {stats.leads > 0 && <Badge size="sm" variant={stats.new > 0 ? "success" : "default"} className="ml-1">{stats.leads}</Badge>}
          </button>
          <button
            onClick={() => setTab("other")}
            className={`pb-2.5 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              tab === "other" ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            Other {stats.other > 0 && <Badge size="sm" className="ml-1">{stats.other}</Badge>}
          </button>
        </div>

        {/* Search + Filters */}
        <div className="flex gap-3 mb-4">
          <div className="flex-1">
            <Input
              type="search" placeholder="Search by name, email, company, subject..."
              value={search} onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && fetchLeads()}
              inputSize="sm"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-border rounded-[var(--radius-sm)] px-2 py-1.5 bg-surface text-text-primary"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="reviewed">Reviewed</option>
            <option value="replied">Replied</option>
            <option value="in_pipeline">In Pipeline</option>
            <option value="dismissed">Dismissed</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="text-xs border border-border rounded-[var(--radius-sm)] px-2 py-1.5 bg-surface text-text-primary"
          >
            <option value="created_at">Newest First</option>
            <option value="confidence">Confidence</option>
            <option value="sender_name">Name A-Z</option>
          </select>
        </div>

        {/* Lead List + Detail Panel */}
        <div className="flex gap-4">
          {/* List */}
          <div className={`${selectedLead ? "w-1/2" : "w-full"} space-y-2 transition-all`}>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="rounded-[var(--radius-md)] border border-border bg-surface p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-2">
                        <Skeleton variant="text" className="w-1/3 h-4" />
                        <Skeleton variant="text" className="w-1/2 h-3" />
                        <Skeleton variant="text" className="w-2/3 h-3" />
                      </div>
                      <Skeleton variant="text" className="w-12 h-3" />
                    </div>
                  </div>
                ))}
              </div>
            ) : leads.length === 0 ? (
              <EmptyState
                icon={<UserFocus className="h-12 w-12" />}
                heading={tab === "leads" ? "No leads yet" : "No other emails"}
                description={tab === "leads"
                  ? "Click 'Sync Now' to check your connected email accounts for new trade inquiries."
                  : "Non-lead emails like newsletters and notifications appear here."
                }
                actionLabel={accounts.length === 0 ? "Connect Email" : "Sync Now"}
                onAction={accounts.length === 0 ? () => window.location.href = "/settings/integrations" : handleSync}
              />
            ) : (
              leads.map((lead) => (
                <Card
                  key={lead.id}
                  hoverable
                  selected={selectedLead?.id === lead.id}
                  onClick={() => openDetail(lead)}
                  className="p-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        {lead.is_high_value && <Star className="h-4 w-4 text-accent" weight="fill" />}
                        <span className="text-sm font-semibold text-text-primary truncate">
                          {lead.sender_name || lead.sender_email}
                        </span>
                        {lead.sender_phone && (
                          <a
                            href={`https://wa.me/${lead.sender_phone.replace(/[^0-9]/g, "")}`}
                            target="_blank" rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-whatsapp hover:text-green-600"
                            title="Open in WhatsApp"
                          >
                            <WhatsappLogo className="h-4 w-4" weight="fill" />
                          </a>
                        )}
                        {lead.status === "new" && <Badge size="sm" variant="success">NEW</Badge>}
                        {lead.status === "reviewed" && <Badge size="sm" variant="outline">Reviewed</Badge>}
                        {lead.status === "replied" && <Badge size="sm" variant="info">Replied</Badge>}
                        {lead.status === "in_pipeline" && <Badge size="sm" variant="whatsapp">In Pipeline</Badge>}
                        {lead.status === "converted" && <Badge size="sm" variant="success">Converted</Badge>}
                        {lead.status === "dismissed" && <Badge size="sm" variant="error">Dismissed</Badge>}
                      </div>
                      {lead.sender_company && (
                        <p className="text-xs text-text-secondary truncate">{lead.sender_company}</p>
                      )}
                      <p className="text-xs text-text-tertiary truncate mt-0.5">
                        {lead.subject || "(no subject)"}
                      </p>

                      {/* Product matches */}
                      {tab === "leads" && lead.products_mentioned.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {lead.products_mentioned.map((p, i) => (
                            <span key={i} className="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                              <Package className="h-3 w-3" />
                              {p.matched_product_name || p.raw}
                              {p.matched_grade_name && ` > ${p.matched_grade_name}`}
                              {p.confidence > 0 && p.confidence < 1 && ` (${Math.round(p.confidence * 100)}%)`}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Tags row */}
                      <div className="flex items-center gap-2 mt-1.5">
                        {lead.delivery_terms && <Badge size="sm" variant="outline">{lead.delivery_terms}</Badge>}
                        {lead.quantities.length > 0 && <Badge size="sm" variant="outline">{lead.quantities[0].raw}</Badge>}
                        {lead.urgency && URGENCY_BADGE[lead.urgency] && (
                          <Badge size="sm" variant={URGENCY_BADGE[lead.urgency].variant}>{URGENCY_BADGE[lead.urgency].label}</Badge>
                        )}
                        {tab === "other" && lead.non_lead_reason && (
                          <Badge size="sm" variant="outline">{NON_LEAD_LABELS[lead.non_lead_reason] || lead.non_lead_reason}</Badge>
                        )}
                      </div>
                    </div>

                    <div className="text-right shrink-0 ml-3">
                      <p className="text-[11px] text-text-tertiary">{formatRelativeTime(lead.received_at)}</p>
                      {lead.thread_message_count > 1 && (
                        <p className="text-[10px] text-text-tertiary mt-0.5">{lead.thread_message_count} msgs</p>
                      )}
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>

          {/* Detail Panel */}
          {selectedLead && (
            <div className="w-1/2 border border-border rounded-[var(--radius-md)] bg-surface overflow-y-auto max-h-[calc(100vh-200px)]">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <h3 className="text-sm font-semibold text-text-primary">Lead Detail</h3>
                <button onClick={() => setSelectedLead(null)} className="text-text-tertiary hover:text-text-primary cursor-pointer">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="p-4 space-y-4">
                {/* Sender Info */}
                <div>
                  <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">Contact</h4>
                  <div className="space-y-1.5">
                    <p className="text-sm font-semibold text-text-primary">{selectedLead.sender_name}</p>
                    {selectedLead.sender_designation && (
                      <p className="text-xs text-text-secondary">{selectedLead.sender_designation}</p>
                    )}
                    {selectedLead.sender_company && (
                      <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                        <Buildings className="h-3.5 w-3.5" /> {selectedLead.sender_company}
                      </div>
                    )}
                    <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                      <EnvelopeSimple className="h-3.5 w-3.5" /> {selectedLead.sender_email}
                    </div>
                    {selectedLead.sender_phone && (
                      <div className="flex items-center gap-3 text-xs text-text-secondary">
                        <div className="flex items-center gap-1.5">
                          <Phone className="h-3.5 w-3.5" /> {selectedLead.sender_phone}
                        </div>
                        <a
                          href={`https://wa.me/${selectedLead.sender_phone.replace(/[^0-9]/g, "")}`}
                          target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-1 text-whatsapp hover:text-green-600 font-medium"
                        >
                          <WhatsappLogo className="h-3.5 w-3.5" weight="fill" /> Chat on WhatsApp
                        </a>
                      </div>
                    )}
                  </div>

                  {/* CRM match suggestion */}
                  {selectedLead.matched_contact_id && (
                    <div className="mt-2 p-2 rounded bg-info/10 text-xs text-blue-700">
                      Matches existing contact in your CRM
                    </div>
                  )}
                  {selectedLead.matched_company_id && !selectedLead.matched_contact_id && (
                    <div className="mt-2 p-2 rounded bg-info/10 text-xs text-blue-700">
                      Company matches: {selectedLead.sender_company}
                    </div>
                  )}
                </div>

                {/* Inquiry Details (leads only) */}
                {selectedLead.classification === "lead" && (
                  <>
                    {selectedLead.products_mentioned.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">Products of Interest</h4>
                        {selectedLead.products_mentioned.map((p, i) => (
                          <div key={i} className="flex items-center justify-between py-1">
                            <div className="flex items-center gap-2">
                              <Package className="h-4 w-4 text-primary" />
                              <span className="text-sm text-text-primary">
                                {p.matched_product_name || p.raw}
                                {p.matched_grade_name && <span className="text-text-secondary"> &gt; {p.matched_grade_name}</span>}
                              </span>
                            </div>
                            {p.confidence > 0 ? (
                              <Badge size="sm" variant={p.confidence >= 0.8 ? "success" : p.confidence >= 0.5 ? "warning" : "error"}>
                                {Math.round(p.confidence * 100)}% match
                              </Badge>
                            ) : (
                              <Badge size="sm" variant="error">No match</Badge>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    <div>
                      <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">Inquiry Details</h4>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {selectedLead.quantities.length > 0 && (
                          <div><span className="text-text-tertiary">Quantity:</span> <span className="text-text-primary font-medium">{selectedLead.quantities[0].raw}</span></div>
                        )}
                        {selectedLead.delivery_terms && (
                          <div><span className="text-text-tertiary">Terms:</span> <span className="text-text-primary font-medium">{selectedLead.delivery_terms}</span></div>
                        )}
                        {selectedLead.destination && (
                          <div><span className="text-text-tertiary">Destination:</span> <span className="text-text-primary font-medium">{selectedLead.destination}</span></div>
                        )}
                        {selectedLead.urgency && (
                          <div><span className="text-text-tertiary">Urgency:</span> <span className="text-text-primary font-medium">{selectedLead.urgency}</span></div>
                        )}
                        {selectedLead.target_price && (
                          <div><span className="text-text-tertiary">Target Price:</span> <span className="text-text-primary font-medium">{selectedLead.target_price}</span></div>
                        )}
                      </div>
                      {selectedLead.specific_questions && (
                        <div className="mt-2 p-2 rounded bg-border-light text-xs text-text-secondary">
                          <span className="font-medium text-text-primary">Questions: </span>
                          {selectedLead.specific_questions}
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Original Email */}
                <div>
                  <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">Original Email</h4>
                  <div className="p-3 rounded-[var(--radius-md)] bg-border-light/50 border border-border">
                    <p className="text-xs font-medium text-text-primary mb-1">{selectedLead.subject}</p>
                    <p className="text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
                      {selectedLead.body_full || selectedLead.body_preview || "(no content)"}
                    </p>
                  </div>
                </div>

                {/* Pipeline Status */}
                {selectedLead.status === "in_pipeline" && (
                  <div className="p-3 rounded-[var(--radius-md)] bg-success/10 border border-success/20">
                    <div className="flex items-center gap-2 mb-1">
                      <Kanban className="h-4 w-4 text-success" weight="bold" />
                      <span className="text-sm font-medium text-green-800">In Pipeline</span>
                    </div>
                    <div className="flex gap-3 text-xs">
                      <a href="/pipeline" className="text-primary hover:underline">View in Pipeline</a>
                      {selectedLead.contact_id && <a href="/contacts" className="text-primary hover:underline">View Contact</a>}
                      {selectedLead.company_id && <a href="/companies" className="text-primary hover:underline">View Company</a>}
                    </div>
                  </div>
                )}

                {/* Status indicator */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-tertiary">Status</span>
                  <select
                    value={selectedLead.status}
                    onChange={async (e) => {
                      try {
                        await api.put(`/leads/${selectedLead.id}`, { status: e.target.value });
                        const { data: updated } = await api.get<Lead>(`/leads/${selectedLead.id}`);
                        setSelectedLead(updated);
                        fetchLeads();
                      } catch { toast.error("Failed to load data"); }
                    }}
                    className="text-xs border border-border rounded-[var(--radius-sm)] px-2 py-1 bg-surface text-text-primary"
                  >
                    <option value="new">New</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="replied">Replied</option>
                    <option value="in_pipeline">In Pipeline</option>
                    <option value="converted">Converted</option>
                    <option value="dismissed">Dismissed</option>
                  </select>
                </div>

                {/* Actions */}
                <div className="border-t border-border pt-4">
                  <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">Actions</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedLead.classification === "lead" ? (
                      <>
                        <Button size="sm" variant="accent" onClick={() => { setShowReplyBar(true); setDraftReply(null); setReplyInstruction(""); setEditedReply(""); }}>
                          <PaperPlaneTilt className="h-3.5 w-3.5 mr-1" /> Draft Reply
                        </Button>
                        {selectedLead.status !== "in_pipeline" && (
                          <Button size="sm" onClick={() => handleMoveToPipeline(selectedLead.id)}>
                            <Kanban className="h-3.5 w-3.5 mr-1" /> Move to Pipeline
                          </Button>
                        )}
                        <Button size="sm" variant="secondary" onClick={() => handleMarkAsNonLead(selectedLead.id)}>
                          <X className="h-3.5 w-3.5 mr-1" /> Not a Lead
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => handleDismiss(selectedLead.id)}>
                          Dismiss
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button size="sm" onClick={() => handleMarkAsLead(selectedLead.id)}>
                          <Check className="h-3.5 w-3.5 mr-1" /> Mark as Lead
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => handleDismiss(selectedLead.id)}>
                          Dismiss
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {/* Reply Composer */}
                {showReplyBar && selectedLead.classification === "lead" && (
                  <div className="border-t border-border pt-4">
                    <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">Reply to {selectedLead.sender_name}</h4>

                    {/* Channel picker */}
                    <div className="flex gap-2 mb-3">
                      <button
                        onClick={() => setReplyChannel("email")}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] text-xs font-medium border transition-colors cursor-pointer ${
                          replyChannel === "email" ? "bg-email/10 text-blue-700 border-email/30" : "bg-surface text-text-secondary border-border hover:border-email/30"
                        }`}
                      >
                        <EnvelopeSimple className="h-3.5 w-3.5" weight="fill" /> Email
                      </button>
                      {selectedLead.sender_phone && (
                        <button
                          onClick={() => setReplyChannel("whatsapp")}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-sm)] text-xs font-medium border transition-colors cursor-pointer ${
                            replyChannel === "whatsapp" ? "bg-whatsapp/10 text-green-700 border-whatsapp/30" : "bg-surface text-text-secondary border-border hover:border-whatsapp/30"
                          }`}
                        >
                          <WhatsappLogo className="h-3.5 w-3.5" weight="fill" /> WhatsApp
                        </button>
                      )}
                    </div>

                    {!draftReply ? (
                      <>
                        <p className="text-xs text-text-secondary mb-2">
                          Tell the AI what to reply via {replyChannel === "whatsapp" ? "WhatsApp" : "Email"}. It will use your catalog, pricing, and preferences.
                        </p>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={replyInstruction}
                            onChange={(e) => setReplyInstruction(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleDraftReply(selectedLead.id)}
                            placeholder="e.g. Send them the quotation for Black Pepper 500GL"
                            className="flex-1 rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light"
                          />
                          <Button size="sm" onClick={() => handleDraftReply(selectedLead.id)} isLoading={drafting}>
                            Draft
                          </Button>
                        </div>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {["Send them the quotation", "Ask for their target price", "Share product specs and MOQ", "Request more details about their requirement"].map((suggestion) => (
                            <button
                              key={suggestion}
                              onClick={() => { setReplyInstruction(suggestion); }}
                              className="text-[11px] px-2 py-1 rounded-[var(--radius-full)] border border-border text-text-tertiary hover:border-primary-lighter hover:text-primary transition-colors cursor-pointer"
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      </>
                    ) : (
                      <>
                        {/* Explanation */}
                        {draftReply.explanation && (
                          <div className="p-2 rounded bg-info/10 text-xs text-blue-700 mb-2">
                            <span className="font-medium">Why this reply: </span>{draftReply.explanation}
                          </div>
                        )}

                        {/* Editable draft */}
                        <textarea
                          value={editedReply}
                          onChange={(e) => setEditedReply(e.target.value)}
                          rows={8}
                          className="w-full rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light resize-y"
                        />

                        <div className="flex items-center justify-between mt-2">
                          <div className="flex gap-2">
                            {replyChannel === "email" ? (
                              <Button size="sm" onClick={() => handleSendReply(selectedLead.id)} isLoading={sending}>
                                <EnvelopeSimple className="h-3.5 w-3.5 mr-1" /> Send via Gmail
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                className="bg-whatsapp hover:bg-green-600 text-white"
                                onClick={() => {
                                  const phone = selectedLead.sender_phone?.replace(/[^0-9]/g, "") || "";
                                  const text = encodeURIComponent(editedReply);
                                  window.open(`https://wa.me/${phone}?text=${text}`, "_blank");
                                }}
                              >
                                <WhatsappLogo className="h-3.5 w-3.5 mr-1" weight="fill" /> Open in WhatsApp
                              </Button>
                            )}
                            <Button size="sm" variant="secondary" onClick={() => { setDraftReply(null); setReplyInstruction(""); }}>
                              Re-draft
                            </Button>
                          </div>
                          <Button size="sm" variant="ghost" onClick={() => { setShowReplyBar(false); setDraftReply(null); }}>
                            Cancel
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </FullWidthLayout>
    </AppShell>
  );
}
