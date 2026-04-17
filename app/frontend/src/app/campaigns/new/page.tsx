"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { MessageTemplate } from "@/types";
import {
  PaperPlaneTilt, WhatsappLogo, EnvelopeSimple,
  ArrowRight, ArrowLeft, Check, Plus, Trash,
  Clock, Users, FileText, Sparkle,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";

interface ContactList {
  id: string; name: string; member_count: number;
}

interface ContactItem {
  id: string; name: string; email: string | null; phone: string | null; company_name: string | null;
}

interface WaStatus {
  status: string; phone: string | null;
}

interface Step {
  channel: string; delay_days: number; condition: string;
  template_content: string; subject_template: string;
  whatsapp_template_name: string;
  message_template_id: string;
}

const SEQUENCE_TEMPLATES = [
  {
    name: "New Buyer Introduction",
    steps: [
      { channel: "whatsapp", delay_days: 0, condition: "always", template_content: "Hi {{name}}, we're {{company}} — exporters of premium {{commodity}}. Would love to share our catalog and pricing.", subject_template: "", whatsapp_template_name: "", message_template_id: "" },
      { channel: "email", delay_days: 3, condition: "no_reply", template_content: "", subject_template: "Introduction: Premium {{commodity}} from {{company}}", whatsapp_template_name: "", message_template_id: "" },
      { channel: "whatsapp", delay_days: 7, condition: "no_reply", template_content: "Hi {{name}}, just following up on my earlier message about {{commodity}}. Happy to share samples!", subject_template: "", whatsapp_template_name: "", message_template_id: "" },
    ],
  },
  {
    name: "Trade Fair Follow-up",
    steps: [
      { channel: "whatsapp", delay_days: 0, condition: "always", template_content: "Hi {{name}}, great meeting you at {{event}}! As discussed, we can offer {{commodity}}.", subject_template: "", whatsapp_template_name: "", message_template_id: "" },
      { channel: "email", delay_days: 2, condition: "always", template_content: "", subject_template: "Follow-up from {{event}} — {{commodity}}", whatsapp_template_name: "", message_template_id: "" },
    ],
  },
  {
    name: "Price Update",
    steps: [
      { channel: "whatsapp", delay_days: 0, condition: "always", template_content: "Hi {{name}}, sharing today's {{commodity}} prices: FOB {{price}}/MT. Available for immediate shipment.", subject_template: "", whatsapp_template_name: "", message_template_id: "" },
    ],
  },
  {
    name: "Custom Sequence",
    steps: [],
  },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);

  // Step 1: Basics
  const [name, setName] = useState("");
  const [campaignType, setCampaignType] = useState("multi_channel");

  // Step 2: Recipients
  const [contactLists, setContactLists] = useState<ContactList[]>([]);
  const [selectedListId, setSelectedListId] = useState("");

  // Step 3: Sequence
  const [selectedTemplate, setSelectedTemplate] = useState(-1);
  const [steps, setSteps] = useState<Step[]>([]);

  // Additional data
  const [allContacts, setAllContacts] = useState<ContactItem[]>([]);
  const [selectedContactIds, setSelectedContactIds] = useState<string[]>([]);
  const [waStatus, setWaStatus] = useState<WaStatus | null>(null);
  const [waTemplates, setWaTemplates] = useState<Array<{ id?: string; template_name?: string; content?: string; status?: string; category?: string; variables?: string[] }>>([]);
  const [msgTemplates, setMsgTemplates] = useState<MessageTemplate[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [listsRes, contactsRes, waRes] = await Promise.all([
          api.get<ContactList[]>("/contact-lists"),
          api.get<{ items: ContactItem[] }>("/contacts?limit=100"),
          api.get<WaStatus>("/whatsapp/status"),
        ]);
        setContactLists(listsRes.data);
        setAllContacts(contactsRes.data.items);
        setWaStatus(waRes.data);

        // Fetch WA templates if connected
        if (waRes.data.status === "active") {
          try {
            const { data: templates } = await api.get<Array<{ id?: string; template_name?: string; content?: string; status?: string; category?: string; variables?: string[] }>>("/whatsapp/templates");
            setWaTemplates(templates);
          } catch { /* silent */ }
        }

        // Fetch message templates
        try {
          const { data: tpls } = await api.get<MessageTemplate[]>("/templates");
          setMsgTemplates(tpls);
        } catch { /* silent */ }
      } catch { toast.error("Failed to load data"); }
    })();
  }, []);

  const addStep = () => {
    setSteps([...steps, {
      channel: "whatsapp", delay_days: steps.length === 0 ? 0 : 3,
      condition: "no_reply", template_content: "", subject_template: "",
      whatsapp_template_name: "", message_template_id: "",
    }]);
  };

  const removeStep = (index: number) => {
    setSteps(steps.filter((_, i) => i !== index));
  };

  const updateStep = (index: number, field: string, value: string | number) => {
    setSteps(steps.map((s, i) => i === index ? { ...s, [field]: value } : s));
  };

  const handleCreate = async () => {
    if (!name.trim()) { toast.error("Campaign name is required"); return; }
    if (steps.length === 0) { toast.error("Add at least one step"); return; }
    setSaving(true);
    try {
      const { data } = await api.post<{ id: string }>("/campaigns", {
        name: name.trim(),
        type: campaignType,
        contact_list_id: selectedListId || undefined,
        steps: steps.map((s, i) => ({
          channel: s.channel,
          delay_days: s.delay_days,
          condition: s.condition,
          template_content: s.template_content,
          subject_template: s.subject_template,
          whatsapp_template_name: s.whatsapp_template_name,
        })),
      });
      toast.success("Campaign created");

      // Auto-launch if contacts selected
      if (selectedContactIds.length > 0) {
        try {
          const { data: launchResult } = await api.post<{ execution?: { sent: number; failed: number; skipped: number } }>(
            `/campaigns/${data.id}/activate`,
            { contact_ids: selectedContactIds },
          );
          if (launchResult.execution) {
            toast.success(`Launched! Sent: ${launchResult.execution.sent}, Failed: ${launchResult.execution.failed}`);
          }
        } catch (err) { toast.error(getErrorMessage(err, "Created but failed to launch")); }
      }

      router.push(`/campaigns/${data.id}`);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create campaign")); }
    setSaving(false);
  };

  return (
    <AppShell title="New Campaign">
      <FullWidthLayout>
        <div className="max-w-3xl mx-auto">
          {/* Progress */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Create Campaign</h2>
            <div className="flex gap-1">
              {[1, 2, 3, 4].map((s) => (
                <div key={s} className={`h-2 w-8 rounded-full transition-colors ${step >= s ? "bg-primary" : "bg-border"}`} />
              ))}
            </div>
          </div>

          {/* Step 1: Basics */}
          {step === 1 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">Campaign Details</h3>
              <div className="space-y-4">
                <Input label="Campaign Name *" placeholder="e.g. Pepper EU Q1 Outreach"
                  value={name} onChange={(e) => setName(e.target.value)} />
                <div>
                  <p className="text-[13px] font-medium text-text-primary mb-2">Channel</p>
                  <div className="flex gap-3">
                    {[
                      { v: "whatsapp", icon: WhatsappLogo, label: "WhatsApp Only", color: "whatsapp" },
                      { v: "email", icon: EnvelopeSimple, label: "Email Only", color: "email" },
                      { v: "multi_channel", icon: PaperPlaneTilt, label: "Multi-Channel", color: "primary" },
                    ].map(({ v, icon: Icon, label, color }) => (
                      <button key={v} onClick={() => setCampaignType(v)}
                        className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-[var(--radius-md)] border transition-all cursor-pointer ${
                          campaignType === v ? `border-${color} bg-${color}/10` : "border-border hover:border-border"
                        }`}>
                        <Icon className={`h-6 w-6 ${campaignType === v ? `text-${color}` : "text-text-tertiary"}`} weight="fill" />
                        <span className={`text-xs font-medium ${campaignType === v ? "text-text-primary" : "text-text-secondary"}`}>{label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex justify-end mt-6">
                <Button onClick={() => { if (!name.trim()) { toast.error("Name required"); return; } setStep(2); }}>
                  Next <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </Card>
          )}

          {/* Step 2: Recipients */}
          {step === 2 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">Select Recipients</h3>

              {/* WhatsApp account info */}
              {(campaignType === "whatsapp" || campaignType === "multi_channel") && (
                <div className={`p-3 rounded-[var(--radius-md)] mb-4 ${waStatus?.status === "active" ? "bg-whatsapp/5 border border-whatsapp/20" : "bg-error/5 border border-error/20"}`}>
                  <div className="flex items-center gap-2">
                    <WhatsappLogo className={`h-4 w-4 ${waStatus?.status === "active" ? "text-whatsapp" : "text-error"}`} weight="fill" />
                    <span className="text-xs font-medium text-text-primary">
                      {waStatus?.status === "active"
                        ? `Sending from: ${waStatus.phone}`
                        : "WhatsApp not connected — connect in Settings > Integrations"}
                    </span>
                  </div>
                </div>
              )}

              {/* Contact Lists */}
              {contactLists.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-text-tertiary uppercase tracking-wide font-semibold mb-2">Contact Lists</p>
                  <div className="space-y-2">
                    {contactLists.map((cl) => (
                      <button key={cl.id} onClick={() => setSelectedListId(cl.id)}
                        className={`w-full flex items-center justify-between p-3 rounded-[var(--radius-md)] border transition-colors cursor-pointer text-left ${
                          selectedListId === cl.id ? "border-primary bg-primary/5" : "border-border hover:border-primary-lighter"
                        }`}>
                        <div className="flex items-center gap-2">
                          <Users className="h-4 w-4 text-text-tertiary" />
                          <span className="text-sm font-medium text-text-primary">{cl.name}</span>
                        </div>
                        <Badge size="sm" variant="outline">{cl.member_count} contacts</Badge>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Individual Contacts */}
              <div>
                <p className="text-xs text-text-tertiary uppercase tracking-wide font-semibold mb-2">
                  Or select individual contacts ({selectedContactIds.length} selected)
                </p>
                {allContacts.length > 0 ? (
                  <div className="max-h-[250px] overflow-y-auto border border-border rounded-[var(--radius-md)]">
                    {allContacts.map((c) => {
                      const isSelected = selectedContactIds.includes(c.id);
                      const hasPhone = !!c.phone;
                      const hasEmail = !!c.email;
                      const canSendWA = (campaignType === "email" || hasPhone);
                      return (
                        <button key={c.id}
                          onClick={() => {
                            if (isSelected) setSelectedContactIds(selectedContactIds.filter((id) => id !== c.id));
                            else setSelectedContactIds([...selectedContactIds, c.id]);
                          }}
                          disabled={!canSendWA && campaignType !== "email"}
                          className={`w-full flex items-center justify-between px-3 py-2 border-b border-border last:border-0 text-left transition-colors ${
                            isSelected ? "bg-primary/5" : "hover:bg-border-light/50"
                          } ${!canSendWA && campaignType !== "email" ? "opacity-40" : "cursor-pointer"}`}
                        >
                          <div className="flex items-center gap-2">
                            <div className={`h-4 w-4 rounded border flex items-center justify-center ${isSelected ? "bg-primary border-primary" : "border-border"}`}>
                              {isSelected && <Check className="h-3 w-3 text-text-inverse" weight="bold" />}
                            </div>
                            <div>
                              <span className="text-sm text-text-primary">{c.name}</span>
                              {c.company_name && <span className="text-xs text-text-tertiary ml-1">({c.company_name})</span>}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {hasPhone && <WhatsappLogo className="h-3.5 w-3.5 text-whatsapp" weight="fill" />}
                            {hasEmail && <EnvelopeSimple className="h-3.5 w-3.5 text-email" weight="fill" />}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-text-tertiary py-4 text-center">No contacts yet. Add contacts first.</p>
                )}
              </div>

              <div className="flex justify-between mt-6">
                <Button variant="ghost" onClick={() => setStep(1)}><ArrowLeft className="h-4 w-4 mr-1" /> Back</Button>
                <Button onClick={() => setStep(3)}>Next <ArrowRight className="h-4 w-4 ml-1" /></Button>
              </div>
            </Card>
          )}

          {/* Step 3: Sequence Builder */}
          {step === 3 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">Build Your Sequence</h3>

              {steps.length === 0 && (
                <>
                  <p className="text-sm text-text-secondary mb-4">Choose a template or build a custom sequence:</p>
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {SEQUENCE_TEMPLATES.map((tmpl, i) => (
                      <button key={i} onClick={() => {
                        setSelectedTemplate(i);
                        setSteps(tmpl.steps.length > 0 ? [...tmpl.steps] : []);
                        if (tmpl.steps.length === 0) addStep();
                      }}
                        className="p-4 rounded-[var(--radius-md)] border border-border text-left hover:border-primary-lighter transition-colors cursor-pointer">
                        <p className="text-sm font-medium text-text-primary mb-1">{tmpl.name}</p>
                        <p className="text-xs text-text-tertiary">
                          {tmpl.steps.length > 0 ? `${tmpl.steps.length} steps` : "Start from scratch"}
                        </p>
                      </button>
                    ))}
                  </div>
                </>
              )}

              {steps.length > 0 && (
                <div className="space-y-3 mb-4">
                  {steps.map((s, i) => (
                    <div key={i} className="relative">
                      {i > 0 && (
                        <div className="flex items-center gap-2 mb-2 ml-6">
                          <Clock className="h-3.5 w-3.5 text-text-tertiary" />
                          <span className="text-xs text-text-secondary">Wait {s.delay_days} day{s.delay_days !== 1 ? "s" : ""}</span>
                          {s.condition !== "always" && (
                            <Badge size="sm" variant="outline">{s.condition === "no_reply" ? "if no reply" : "if not opened"}</Badge>
                          )}
                        </div>
                      )}
                      <div className="flex gap-3 p-3 rounded-[var(--radius-md)] border border-border bg-surface">
                        <div className="flex flex-col items-center gap-1">
                          <div className={`h-8 w-8 rounded-full flex items-center justify-center text-text-inverse text-xs font-bold ${
                            s.channel === "whatsapp" ? "bg-whatsapp" : "bg-email"
                          }`}>
                            {i + 1}
                          </div>
                        </div>
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <select value={s.channel} onChange={(e) => updateStep(i, "channel", e.target.value)}
                              className="text-xs border border-border rounded px-2 py-1 bg-surface">
                              <option value="whatsapp">WhatsApp</option>
                              <option value="email">Email</option>
                            </select>
                            {i > 0 && (
                              <>
                                <select value={s.delay_days.toString()} onChange={(e) => updateStep(i, "delay_days", parseInt(e.target.value))}
                                  className="text-xs border border-border rounded px-2 py-1 bg-surface">
                                  {[0,1,2,3,5,7,14].map((d) => <option key={d} value={d}>Wait {d} day{d !== 1 ? "s" : ""}</option>)}
                                </select>
                                <select value={s.condition} onChange={(e) => updateStep(i, "condition", e.target.value)}
                                  className="text-xs border border-border rounded px-2 py-1 bg-surface">
                                  <option value="always">Always</option>
                                  <option value="no_reply">If no reply</option>
                                  <option value="no_open">If not opened</option>
                                </select>
                              </>
                            )}
                            <button onClick={() => removeStep(i)} className="ml-auto text-text-tertiary hover:text-error cursor-pointer">
                              <Trash className="h-4 w-4" />
                            </button>
                          </div>
                          {/* WhatsApp template selector */}
                          {s.channel === "whatsapp" && (
                            <p className="text-[10px] text-warning">
                              WhatsApp requires approved templates for first-touch messages. {waTemplates.length === 0 ? "Connect WhatsApp in Settings to load templates." : ""}
                            </p>
                          )}
                          {s.channel === "whatsapp" && waTemplates.length > 0 && (
                            <select
                              value={s.whatsapp_template_name}
                              onChange={(e) => {
                                updateStep(i, "whatsapp_template_name", e.target.value);
                                const tmpl = waTemplates.find((t) => t.template_name === e.target.value);
                                if (tmpl && tmpl.content) {
                                  updateStep(i, "template_content", tmpl.content);
                                }
                              }}
                              className="text-xs border border-border rounded px-2 py-1 bg-surface w-full"
                            >
                              <option value="">Select an approved template</option>
                              {waTemplates
                                .filter((t) => t.status === "ENABLED" || t.status === "APPROVED" || t.status === "approved")
                                .map((t) => (
                                  <option key={t.template_name} value={t.template_name}>
                                    {t.template_name} ({t.category}) — {(t.variables || []).length} variable{(t.variables || []).length !== 1 ? "s" : ""}
                                  </option>
                                ))
                              }
                            </select>
                          )}
                          {s.channel === "email" && (
                            <Input inputSize="sm" placeholder="Email subject..." value={s.subject_template}
                              onChange={(e) => updateStep(i, "subject_template", e.target.value)} />
                          )}
                          {/* Template picker */}
                          <div className="flex items-center gap-2">
                            <select
                              value={s.message_template_id}
                              onChange={(e) => {
                                const tplId = e.target.value;
                                updateStep(i, "message_template_id", tplId);
                                if (tplId) {
                                  const tpl = msgTemplates.find((t) => t.id === tplId);
                                  if (tpl) {
                                    updateStep(i, "template_content", tpl.body);
                                    if (tpl.subject) updateStep(i, "subject_template", tpl.subject);
                                  }
                                }
                              }}
                              className="text-xs border border-border rounded px-2 py-1 bg-surface flex-1"
                            >
                              <option value="">Use a template...</option>
                              {msgTemplates
                                .filter((t) => t.channel === s.channel)
                                .map((t) => (
                                  <option key={t.id} value={t.id}>{t.name}</option>
                                ))
                              }
                            </select>
                            <button onClick={() => router.push("/settings/templates/new")}
                              className="text-xs text-primary hover:underline cursor-pointer flex items-center gap-0.5 shrink-0">
                              <Sparkle className="h-3 w-3" /> Create new
                            </button>
                          </div>
                          <textarea
                            value={s.template_content}
                            onChange={(e) => updateStep(i, "template_content", e.target.value)}
                            placeholder={s.channel === "whatsapp"
                              ? "WhatsApp message... Use {{contact_first_name}}, {{company_name}}, {{product}} for personalization"
                              : "Email body... Use {{contact_first_name}}, {{company_name}}, {{product}} for personalization"
                            }
                            rows={3}
                            className="w-full text-xs rounded border border-border px-2 py-1.5 bg-surface text-text-primary placeholder:text-text-tertiary resize-y focus:outline-none focus:ring-1 focus:ring-primary/20"
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  <button onClick={addStep}
                    className="w-full p-2 border border-dashed border-border rounded-[var(--radius-md)] text-xs text-text-tertiary hover:text-primary hover:border-primary-lighter transition-colors cursor-pointer">
                    <Plus className="h-3.5 w-3.5 inline mr-1" /> Add Step
                  </button>
                </div>
              )}

              <div className="flex justify-between mt-6">
                <Button variant="ghost" onClick={() => setStep(2)}><ArrowLeft className="h-4 w-4 mr-1" /> Back</Button>
                <Button onClick={() => { if (steps.length === 0) { toast.error("Add at least one step"); return; } setStep(4); }}>
                  Review <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </Card>
          )}

          {/* Step 4: Review & Preview */}
          {step === 4 && (() => {
            // Get preview contacts (first 5 selected or from list)
            const previewContacts = selectedContactIds.length > 0
              ? allContacts.filter((c) => selectedContactIds.includes(c.id)).slice(0, 5)
              : allContacts.slice(0, 5);

            const personalize = (text: string, contact: ContactItem) => {
              return text
                .replace(/\{\{name\}\}/gi, contact.name.split(" ")[0])
                .replace(/\{\{full_name\}\}/gi, contact.name)
                .replace(/\{\{company\}\}/gi, contact.company_name || "your company")
                .replace(/\{\{commodity\}\}/gi, "our products");
            };

            return (
              <Card>
                <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">Review & Preview</h3>

                {/* Summary */}
                <div className="space-y-2 mb-4 p-3 rounded-[var(--radius-md)] bg-border-light/50">
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Campaign</span>
                    <span className="font-medium text-text-primary">{name}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Channel</span>
                    <Badge size="sm" variant={campaignType === "whatsapp" ? "whatsapp" : campaignType === "email" ? "email" : "default"}>
                      {campaignType === "multi_channel" ? "Multi-Channel" : campaignType}
                    </Badge>
                  </div>
                  {(campaignType === "whatsapp" || campaignType === "multi_channel") && waStatus?.phone && (
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">WhatsApp Number</span>
                      <span className="font-medium text-text-primary flex items-center gap-1">
                        <WhatsappLogo className="h-3.5 w-3.5 text-whatsapp" weight="fill" /> {waStatus.phone}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Recipients</span>
                    <span className="font-medium text-text-primary">
                      {selectedContactIds.length > 0 ? `${selectedContactIds.length} contacts` :
                       selectedListId ? contactLists.find((l) => l.id === selectedListId)?.name : "None selected"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Steps</span>
                    <span className="font-medium text-text-primary">{steps.length}</span>
                  </div>
                </div>

                {/* Sequence flow */}
                <div className="mb-4">
                  <p className="text-xs text-text-tertiary uppercase tracking-wide font-semibold mb-2">Sequence</p>
                  {steps.map((s, i) => (
                    <div key={i} className="flex items-center gap-2 py-1">
                      <div className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold text-text-inverse ${
                        s.channel === "whatsapp" ? "bg-whatsapp" : "bg-email"
                      }`}>{i + 1}</div>
                      <span className="text-xs text-text-primary">{s.channel === "whatsapp" ? "WhatsApp" : "Email"}</span>
                      {s.whatsapp_template_name && <Badge size="sm" variant="outline">Template: {s.whatsapp_template_name}</Badge>}
                      {i > 0 && <span className="text-xs text-text-tertiary">after {s.delay_days}d</span>}
                      {s.condition !== "always" && <Badge size="sm" variant="outline">{s.condition}</Badge>}
                    </div>
                  ))}
                </div>

                {/* Message Previews per contact */}
                {previewContacts.length > 0 && steps.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-text-tertiary uppercase tracking-wide font-semibold mb-2">
                      Message Preview (Step 1 — first {previewContacts.length} recipients)
                    </p>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {previewContacts.map((contact) => {
                        const firstStep = steps[0];
                        const preview = personalize(firstStep.template_content, contact);
                        return (
                          <div key={contact.id} className={`p-3 rounded-[var(--radius-md)] border ${firstStep.channel === "whatsapp" ? "bg-[#DCF8C6]/30 border-whatsapp/20" : "bg-blue-50/30 border-email/20"}`}>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium text-text-primary">To: {contact.name}</span>
                              <span className="text-[10px] text-text-tertiary">
                                {firstStep.channel === "whatsapp" ? contact.phone || "no phone" : contact.email || "no email"}
                              </span>
                            </div>
                            {firstStep.channel === "email" && firstStep.subject_template && (
                              <p className="text-xs font-medium text-text-primary mb-1">
                                Subject: {personalize(firstStep.subject_template, contact)}
                              </p>
                            )}
                            <p className="text-xs text-text-secondary whitespace-pre-wrap">{preview || "(empty message)"}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="flex justify-between">
                  <Button variant="ghost" onClick={() => setStep(3)}><ArrowLeft className="h-4 w-4 mr-1" /> Back</Button>
                  <Button onClick={handleCreate} isLoading={saving}>
                    <Check className="h-4 w-4 mr-1" /> {selectedContactIds.length > 0 ? `Create & Send to ${selectedContactIds.length} contacts` : "Create Campaign (Draft)"}
                  </Button>
                </div>
              </Card>
            );
          })()}
        </div>
      </FullWidthLayout>
    </AppShell>
  );
}
