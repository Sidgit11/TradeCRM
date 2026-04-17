"use client";
import type { PipelineOpportunity as Opportunity, PipelineStage as Stage, InsightsResponse, InsightItem } from "@/types";

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
  ArrowLeft, PencilSimple, Buildings, User, Package,
  CurrencyDollar, CalendarBlank, Scales, Truck, TestTube,
  Notebook, ArrowsClockwise, Warning, Tag, ChartBar,
  MagnifyingGlass, Check, Clock, X as XIcon, Anchor, Sparkle,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { ProductPicker } from "@/components/ui/ProductPicker";
import { toast } from "sonner";
import { formatRelativeTime, formatNumber } from "@/lib/utils";

const INCOTERMS = ["FOB", "CFR", "CIF", "CnF", "EXW", "DDP"];
const PAYMENT_TERMS = ["LC at Sight", "TT Advance", "CAD", "DA", "Open Account", "LC 30 Days", "LC 60 Days", "LC 90 Days"];
const CONTAINER_TYPES = ["20ft", "40ft", "40ft HC"];

function InfoRow({ icon: Icon, label, value, href, children }: { icon: React.ElementType; label: string; value?: string | number | null; href?: string; children?: React.ReactNode }) {
  if (!value && value !== 0 && !children) return null;
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="h-4 w-4 text-text-tertiary mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-[11px] text-text-tertiary uppercase tracking-wide">{label}</p>
        {children ? children : href ? (
          <a href={href} className="text-sm text-primary hover:underline break-all">{String(value)}</a>
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

export default function OpportunityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEdit, setShowEdit] = useState(false);
  const [editSection, setEditSection] = useState("");
  const [saving, setSaving] = useState(false);
  const [editData, setEditData] = useState<Record<string, string | boolean>>({});
  const [movingTo, setMovingTo] = useState<string | null>(null);
  const [insights, setInsights] = useState<InsightItem[]>([]);

  const fetchOpportunity = useCallback(async () => {
    setLoading(true);
    try {
      const [oppRes, stagesRes] = await Promise.all([
        api.get<Opportunity>(`/pipeline/${id}`),
        api.get<Stage[]>("/pipeline/stages"),
      ]);
      setOpportunity(oppRes.data);
      setStages(stagesRes.data);
    } catch { toast.error("Failed to load opportunity"); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchOpportunity(); }, [fetchOpportunity]);
  useEffect(() => { if (id) api.get<InsightsResponse>(`/insights/opportunity/${id}`).then(({ data }) => setInsights(data.insights || [])).catch(() => {}); }, [id]);

  const openEdit = (section: string) => {
    if (!opportunity) return;
    const o = opportunity;
    const data: Record<string, string | boolean> = {};

    if (section === "overview") {
      data.title = o.title || ""; data.commodity = o.commodity || "";
      data.quantity_mt = o.quantity_mt?.toString() || "";
      data.probability = o.probability?.toString() || "0";
      data.expected_close_date = o.expected_close_date || "";
      data.follow_up_date = o.follow_up_date || "";
    } else if (section === "pricing") {
      data.target_price = o.target_price?.toString() || "";
      data.our_price = o.our_price?.toString() || "";
      data.competitor_price = o.competitor_price?.toString() || "";
      data.estimated_value_usd = o.estimated_value_usd?.toString() || "";
      data.incoterms = o.incoterms || "";
      data.payment_terms = o.payment_terms || "";
    } else if (section === "shipping") {
      data.container_type = o.container_type || "";
      data.number_of_containers = o.number_of_containers?.toString() || "";
      data.target_shipment_date = o.target_shipment_date || "";
      data.shipping_line = o.shipping_line || "";
      data.packaging_requirements = o.packaging_requirements || "";
    } else if (section === "quality") {
      data.sample_sent = o.sample_sent;
      data.sample_sent_date = o.sample_sent_date || "";
      data.sample_approved = o.sample_approved === true ? "true" : o.sample_approved === false ? "false" : "";
      data.sample_feedback = o.sample_feedback || "";
    } else if (section === "notes") {
      data.notes = o.notes || "";
      data.loss_reason = o.loss_reason || "";
      data.assigned_to = o.assigned_to || "";
      data.tags = (o.tags || []).join(", ");
    }

    setEditData(data);
    setEditSection(section);
    setShowEdit(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};

      if (editSection === "overview") {
        Object.assign(payload, {
          title: (editData.title as string)?.trim() || null,
          commodity: (editData.commodity as string)?.trim() || null,
          quantity_mt: editData.quantity_mt ? parseFloat(editData.quantity_mt as string) : null,
          probability: editData.probability ? parseInt(editData.probability as string) : 0,
          expected_close_date: (editData.expected_close_date as string) || null,
          follow_up_date: (editData.follow_up_date as string) || null,
        });
      } else if (editSection === "pricing") {
        Object.assign(payload, {
          target_price: editData.target_price ? parseFloat(editData.target_price as string) : null,
          our_price: editData.our_price ? parseFloat(editData.our_price as string) : null,
          competitor_price: editData.competitor_price ? parseFloat(editData.competitor_price as string) : null,
          estimated_value_usd: editData.estimated_value_usd ? parseFloat(editData.estimated_value_usd as string) : null,
          incoterms: (editData.incoterms as string) || null,
          payment_terms: (editData.payment_terms as string) || null,
        });
      } else if (editSection === "shipping") {
        Object.assign(payload, {
          container_type: (editData.container_type as string) || null,
          number_of_containers: editData.number_of_containers ? parseInt(editData.number_of_containers as string) : null,
          target_shipment_date: (editData.target_shipment_date as string) || null,
          shipping_line: (editData.shipping_line as string)?.trim() || null,
          packaging_requirements: (editData.packaging_requirements as string)?.trim() || null,
        });
      } else if (editSection === "quality") {
        Object.assign(payload, {
          sample_sent: editData.sample_sent as boolean,
          sample_sent_date: (editData.sample_sent_date as string) || null,
          sample_approved: editData.sample_approved === "true" ? true : editData.sample_approved === "false" ? false : null,
          sample_feedback: (editData.sample_feedback as string)?.trim() || null,
        });
      } else if (editSection === "notes") {
        const csvToArr = (s: string) => s ? s.split(",").map((v) => v.trim()).filter(Boolean) : undefined;
        Object.assign(payload, {
          notes: (editData.notes as string)?.trim() || null,
          loss_reason: (editData.loss_reason as string)?.trim() || null,
        });
        // tags not in OpportunityUpdate yet — skip for now
      }

      await api.put(`/pipeline/${id}`, payload);
      toast.success("Opportunity updated");
      setShowEdit(false);
      fetchOpportunity();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to update")); }
    setSaving(false);
  };

  const handleMoveToStage = async (stageId: string) => {
    setMovingTo(stageId);
    try {
      await api.put(`/pipeline/${id}/move`, { stage_id: stageId });
      const stageName = stages.find((s) => s.id === stageId)?.name;
      toast.success(`Moved to ${stageName}`);
      fetchOpportunity();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to move")); }
    setMovingTo(null);
  };

  const handleArchive = async () => {
    if (!confirm("Archive this opportunity? It will be hidden from the board.")) return;
    try {
      await api.delete(`/pipeline/${id}`);
      toast.success("Opportunity archived");
      router.push("/opportunities");
    } catch (err) { toast.error(getErrorMessage(err, "Failed to archive")); }
  };

  const setEd = (k: string, v: string | boolean) => setEditData((d) => ({ ...d, [k]: v }));

  function ChipSelect({ options, field, label }: { options: string[]; field: string; label?: string }) {
    return (
      <div>
        {label && <p className="text-[13px] font-medium text-text-primary mb-1.5">{label}</p>}
        <div className="flex flex-wrap gap-1.5">
          {options.map((t) => (
            <button key={t} onClick={() => setEd(field, editData[field] === t ? "" : t)}
              className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                editData[field] === t ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
              }`}>{t}</button>
          ))}
        </div>
      </div>
    );
  }

  if (loading) {
    return <AppShell title="Opportunity"><FullWidthLayout><Skeleton variant="card" className="h-32 mb-4" /><Skeleton variant="card" className="h-64" /></FullWidthLayout></AppShell>;
  }

  if (!opportunity) {
    return <AppShell title="Opportunity"><FullWidthLayout><p className="text-sm text-text-secondary">Opportunity not found</p></FullWidthLayout></AppShell>;
  }

  const o = opportunity;
  const daysOpen = Math.floor((Date.now() - new Date(o.created_at).getTime()) / 86400000);

  return (
    <AppShell title={o.title || "Opportunity"}>
      <FullWidthLayout>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/opportunities")} className="text-text-tertiary hover:text-text-primary cursor-pointer">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
                  {o.title || "Untitled Opportunity"}
                </h2>
                {o.stage_name && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-medium text-white" style={{ backgroundColor: o.stage_color || "#6B7280" }}>
                    {o.stage_name}
                  </span>
                )}
                <Badge size="sm" variant="outline" className="capitalize">{o.source}</Badge>
              </div>
              <p className="text-xs text-text-tertiary mt-0.5">
                {o.display_id || o.id.slice(0, 8)} · Added {formatRelativeTime(o.created_at)} · Updated {formatRelativeTime(o.updated_at)}
                {o.closed_at && ` · Closed ${formatRelativeTime(o.closed_at)}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={fetchOpportunity}><ArrowsClockwise className="h-4 w-4 mr-1" /> Refresh</Button>
            <Button variant="ghost" className="text-error hover:bg-error/10" onClick={handleArchive}>Archive</Button>
          </div>
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
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-primary">
              {o.estimated_value_usd || o.value ? `$${formatNumber(o.estimated_value_usd || o.value || 0)}` : "—"}
            </p>
            <p className="text-xs text-text-tertiary">Deal Value</p>
          </Card>
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{o.probability}%</p>
            <p className="text-xs text-text-tertiary">Probability</p>
          </Card>
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
              {o.quantity_mt ? `${formatNumber(o.quantity_mt)} MT` : "—"}
            </p>
            <p className="text-xs text-text-tertiary">Quantity</p>
          </Card>
          <Card className="p-3 text-center">
            <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{daysOpen}</p>
            <p className="text-xs text-text-tertiary">Days Open</p>
          </Card>
        </div>

        {/* Stage Actions */}
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-text-primary">Move to Stage</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {stages.map((stage) => (
              <button
                key={stage.id}
                onClick={() => handleMoveToStage(stage.id)}
                disabled={stage.id === o.stage_id || movingTo !== null}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                  stage.id === o.stage_id
                    ? "text-white border-transparent"
                    : "bg-surface text-text-secondary border-border hover:border-primary/30 hover:text-primary"
                } ${movingTo === stage.id ? "opacity-50" : ""}`}
                style={stage.id === o.stage_id ? { backgroundColor: stage.color } : undefined}
              >
                {stage.id === o.stage_id && <Check className="h-3 w-3 inline mr-1" />}
                {stage.name}
              </button>
            ))}
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Deal Overview */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Deal Overview</h3>
              <button onClick={() => openEdit("overview")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={Package} label="Title" value={o.title} />
              <InfoRow icon={Package} label="Commodity" value={o.commodity} />
              <InfoRow icon={Scales} label="Quantity" value={o.quantity_mt ? `${o.quantity_mt} MT` : null} />
              <InfoRow icon={MagnifyingGlass} label="Source" value={o.source} />
              <InfoRow icon={ChartBar} label="Probability" value={o.probability ? `${o.probability}%` : null} />
              <InfoRow icon={CalendarBlank} label="Expected Close" value={o.expected_close_date} />
              <InfoRow icon={CalendarBlank} label="Follow-up Date" value={o.follow_up_date} />
            </div>
          </Card>

          {/* Pricing & Terms */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Pricing & Terms</h3>
              <button onClick={() => openEdit("pricing")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={CurrencyDollar} label="Target Price" value={o.target_price ? `$${formatNumber(o.target_price)}/MT` : null} />
              <InfoRow icon={CurrencyDollar} label="Our Price" value={o.our_price ? `$${formatNumber(o.our_price)}/MT` : null} />
              <InfoRow icon={CurrencyDollar} label="Competitor Price" value={o.competitor_price ? `$${formatNumber(o.competitor_price)}/MT` : null} />
              <InfoRow icon={CurrencyDollar} label="Estimated Value" value={o.estimated_value_usd ? `$${formatNumber(o.estimated_value_usd)}` : null} />
              <InfoRow icon={Scales} label="Incoterms" value={o.incoterms} />
              <InfoRow icon={CurrencyDollar} label="Payment Terms" value={o.payment_terms} />
              <InfoRow icon={CurrencyDollar} label="Currency" value={o.currency} />
            </div>
          </Card>

          {/* Company & Contact */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Company & Contact</h3>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={Buildings} label="Company" value={o.company_name}>
                <a href={`/companies/${o.company_id}`} className="text-sm text-primary hover:underline font-medium">
                  {o.company_name || "Unknown"}
                </a>
              </InfoRow>
              {o.contact_id && (
                <InfoRow icon={User} label="Contact" value={o.contact_name}>
                  <a href={`/contacts/${o.contact_id}`} className="text-sm text-primary hover:underline font-medium">
                    {o.contact_name || "Unknown"}
                  </a>
                </InfoRow>
              )}
            </div>
          </Card>

          {/* Shipping & Logistics */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Shipping & Logistics</h3>
              <button onClick={() => openEdit("shipping")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="divide-y divide-border">
              <InfoRow icon={Truck} label="Container Type" value={o.container_type} />
              <InfoRow icon={Truck} label="Number of Containers" value={o.number_of_containers} />
              <InfoRow icon={CalendarBlank} label="Target Shipment Date" value={o.target_shipment_date} />
              <InfoRow icon={Anchor} label="Shipping Line" value={o.shipping_line} />
              <InfoRow icon={Package} label="Packaging" value={o.packaging_requirements} />
            </div>
          </Card>

          {/* Quality & Samples */}
          <Card className="relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Quality & Samples</h3>
              <button onClick={() => openEdit("quality")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>

            {/* Quality specifications */}
            {o.quality_specifications && Object.keys(o.quality_specifications).length > 0 && (
              <div className="mb-3">
                <p className="text-[11px] text-text-tertiary uppercase tracking-wide mb-2">Specifications</p>
                <div className="space-y-1">
                  {Object.entries(o.quality_specifications).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-text-secondary">{key}</span>
                      <span className="text-text-primary font-medium">{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sample timeline */}
            {o.sample_sent && (
              <div className="mb-3">
                <p className="text-[11px] text-text-tertiary uppercase tracking-wide mb-2">Sample Tracking</p>
                <div className="flex items-center gap-0">
                  {/* Step 1: Sent */}
                  <div className="flex items-center gap-1.5">
                    <div className="w-6 h-6 rounded-full bg-success/10 flex items-center justify-center">
                      <Check className="h-3.5 w-3.5 text-success" />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-success">Sent</p>
                      {o.sample_sent_date && <p className="text-[10px] text-text-tertiary">{o.sample_sent_date}</p>}
                    </div>
                  </div>
                  <div className="w-8 h-px bg-border mx-1" />
                  {/* Step 2: Review */}
                  <div className="flex items-center gap-1.5">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                      o.sample_approved === null ? "bg-warning/10" : o.sample_approved ? "bg-success/10" : "bg-error/10"
                    }`}>
                      {o.sample_approved === null ? (
                        <Clock className="h-3.5 w-3.5 text-warning" />
                      ) : o.sample_approved ? (
                        <Check className="h-3.5 w-3.5 text-success" />
                      ) : (
                        <XIcon className="h-3.5 w-3.5 text-error" />
                      )}
                    </div>
                    <p className={`text-xs font-medium ${
                      o.sample_approved === null ? "text-warning" : o.sample_approved ? "text-success" : "text-error"
                    }`}>
                      {o.sample_approved === null ? "Awaiting" : o.sample_approved ? "Approved" : "Rejected"}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {!o.sample_sent && (
              <p className="text-xs text-text-tertiary py-2">No sample sent yet</p>
            )}

            {o.sample_feedback && (
              <div className="divide-y divide-border">
                <InfoRow icon={Notebook} label="Feedback" value={o.sample_feedback} />
              </div>
            )}
          </Card>

          {/* Notes & Meta */}
          <Card className="lg:col-span-2 relative">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-primary">Notes & Meta</h3>
              <button onClick={() => openEdit("notes")} className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-1">
                <PencilSimple className="h-3.5 w-3.5" /> Edit
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
              <div className="divide-y divide-border">
                <InfoRow icon={User} label="Assigned To" value={o.assigned_to} />
                {o.loss_reason && <InfoRow icon={Warning} label="Loss Reason" value={o.loss_reason} />}
              </div>
              <div>
                <TagList items={o.tags} label="Tags" />
              </div>
            </div>
            {o.notes && (
              <div className="mt-3 pt-3 border-t border-border">
                <div className="flex items-start gap-3">
                  <Notebook className="h-4 w-4 text-text-tertiary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wide">Notes</p>
                    <p className="text-sm text-text-primary whitespace-pre-wrap">{o.notes}</p>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Edit Modal */}
        <Modal open={showEdit} onOpenChange={setShowEdit}
          title={`Edit ${
            editSection === "overview" ? "Deal Overview" :
            editSection === "pricing" ? "Pricing & Terms" :
            editSection === "shipping" ? "Shipping & Logistics" :
            editSection === "quality" ? "Quality & Samples" : "Notes & Meta"
          }`}
          size="md"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <Button variant="secondary" onClick={() => setShowEdit(false)}>Cancel</Button>
              <Button onClick={handleSave} isLoading={saving}>Save Changes</Button>
            </div>
          }
        >
          <div className="space-y-4">
            {editSection === "overview" && <>
              <Input label="Title" value={editData.title as string || ""} onChange={(e) => setEd("title", e.target.value)} />
              <ProductPicker label="Commodity" value={(editData.commodity as string) ? [editData.commodity as string] : []}
                onChange={(v) => setEd("commodity", v[0] || "")} multi={false} placeholder="Select from your catalog..." />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Quantity (MT)" type="number" value={editData.quantity_mt as string || ""} onChange={(e) => setEd("quantity_mt", e.target.value)} />
                <Input label="Probability (%)" type="number" value={editData.probability as string || ""} onChange={(e) => setEd("probability", e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Expected Close Date" type="date" value={editData.expected_close_date as string || ""} onChange={(e) => setEd("expected_close_date", e.target.value)} />
                <Input label="Follow-up Date" type="date" value={editData.follow_up_date as string || ""} onChange={(e) => setEd("follow_up_date", e.target.value)} />
              </div>
            </>}

            {editSection === "pricing" && <>
              <div className="grid grid-cols-3 gap-4">
                <Input label="Target Price ($/MT)" type="number" value={editData.target_price as string || ""} onChange={(e) => setEd("target_price", e.target.value)} />
                <Input label="Our Price ($/MT)" type="number" value={editData.our_price as string || ""} onChange={(e) => setEd("our_price", e.target.value)} />
                <Input label="Competitor Price ($/MT)" type="number" value={editData.competitor_price as string || ""} onChange={(e) => setEd("competitor_price", e.target.value)} />
              </div>
              <Input label="Estimated Deal Value ($)" type="number" value={editData.estimated_value_usd as string || ""} onChange={(e) => setEd("estimated_value_usd", e.target.value)} />
              <ChipSelect field="incoterms" label="Incoterms" options={INCOTERMS} />
              <ChipSelect field="payment_terms" label="Payment Terms" options={PAYMENT_TERMS} />
            </>}

            {editSection === "shipping" && <>
              <ChipSelect field="container_type" label="Container Type" options={CONTAINER_TYPES} />
              <div className="grid grid-cols-2 gap-4">
                <Input label="Number of Containers" type="number" value={editData.number_of_containers as string || ""} onChange={(e) => setEd("number_of_containers", e.target.value)} />
                <Input label="Target Shipment Date" type="date" value={editData.target_shipment_date as string || ""} onChange={(e) => setEd("target_shipment_date", e.target.value)} />
              </div>
              <Input label="Shipping Line" value={editData.shipping_line as string || ""} onChange={(e) => setEd("shipping_line", e.target.value)} />
              <Textarea label="Packaging Requirements" value={editData.packaging_requirements as string || ""} onChange={(e) => setEd("packaging_requirements", e.target.value)} rows={2} />
            </>}

            {editSection === "quality" && <>
              <div>
                <p className="text-[13px] font-medium text-text-primary mb-1.5">Sample Sent</p>
                <div className="flex gap-2">
                  {[true, false].map((v) => (
                    <button key={String(v)} onClick={() => setEd("sample_sent", v)}
                      className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                        editData.sample_sent === v ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                      }`}>{v ? "Yes" : "No"}</button>
                  ))}
                </div>
              </div>
              {editData.sample_sent && (
                <Input label="Sample Sent Date" type="date" value={editData.sample_sent_date as string || ""} onChange={(e) => setEd("sample_sent_date", e.target.value)} />
              )}
              <div>
                <p className="text-[13px] font-medium text-text-primary mb-1.5">Sample Approved</p>
                <div className="flex gap-2">
                  {[{ label: "Pending", val: "" }, { label: "Approved", val: "true" }, { label: "Rejected", val: "false" }].map(({ label, val }) => (
                    <button key={val} onClick={() => setEd("sample_approved", val)}
                      className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                        editData.sample_approved === val
                          ? val === "true" ? "bg-success/10 text-success border-success/30" : val === "false" ? "bg-error/10 text-error border-error/30" : "bg-warning/10 text-warning border-warning/30"
                          : "bg-surface text-text-secondary border-border"
                      }`}>{label}</button>
                  ))}
                </div>
              </div>
              <Textarea label="Sample Feedback" value={editData.sample_feedback as string || ""} onChange={(e) => setEd("sample_feedback", e.target.value)} rows={3} />
            </>}

            {editSection === "notes" && <>
              <Textarea label="Notes" value={editData.notes as string || ""} onChange={(e) => setEd("notes", e.target.value)} rows={4} />
              <Input label="Loss Reason" placeholder="If deal is lost, explain why" value={editData.loss_reason as string || ""} onChange={(e) => setEd("loss_reason", e.target.value)} />
              <Input label="Tags (comma-separated)" value={editData.tags as string || ""} onChange={(e) => setEd("tags", e.target.value)} />
            </>}
          </div>
        </Modal>
      </FullWidthLayout>
    </AppShell>
  );
}
