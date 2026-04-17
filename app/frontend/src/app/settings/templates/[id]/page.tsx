"use client";
import type { MessageTemplate, TemplateVariable } from "@/types";

import { useState, useEffect, useCallback, use, useRef } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  ArrowLeft, FloppyDisk, EnvelopeSimple, WhatsappLogo, Sparkle,
  TextAa, ArrowsOutSimple, ArrowsInSimple, HandWaving, Megaphone,
  Hash, Eye, Code,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime } from "@/lib/utils";

const CATEGORIES = ["introduction", "price_update", "follow_up", "sample_offer", "order_confirmation", "festive_greeting", "reactivation", "custom"];
const CATEGORY_LABELS: Record<string, string> = {
  introduction: "Introduction", price_update: "Price Update", follow_up: "Follow Up",
  sample_offer: "Sample Offer", order_confirmation: "Order Confirm", festive_greeting: "Festive",
  reactivation: "Reactivation", custom: "Custom",
};

export default function TemplateEditorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const bodyRef = useRef<HTMLTextAreaElement>(null);

  const [template, setTemplate] = useState<MessageTemplate | null>(null);
  const [variables, setVariables] = useState<TemplateVariable[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refining, setRefining] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [showVarPicker, setShowVarPicker] = useState(false);

  // Edit state
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [description, setDescription] = useState("");

  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    try {
      const [tRes, vRes] = await Promise.all([
        api.get<MessageTemplate>(`/templates/${id}`),
        api.get<TemplateVariable[]>("/templates/variables"),
      ]);
      const t = tRes.data;
      setTemplate(t);
      setVariables(vRes.data);
      setName(t.name); setCategory(t.category);
      setSubject(t.subject || ""); setBody(t.body);
      setDescription(t.description || "");
    } catch { toast.error("Failed to load template"); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchTemplate(); }, [fetchTemplate]);

  const handleSave = async () => {
    if (!name.trim()) { toast.error("Name is required"); return; }
    if (!body.trim()) { toast.error("Body is required"); return; }
    setSaving(true);
    try {
      await api.put(`/templates/${id}`, {
        name: name.trim(),
        category,
        subject: template?.channel === "email" ? subject.trim() || null : null,
        body: body.trim(),
        description: description.trim() || null,
      });
      toast.success("Template saved");
      fetchTemplate();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to save")); }
    setSaving(false);
  };

  const insertVariable = (key: string) => {
    const textarea = bodyRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = `{{${key}}}`;
    const newBody = body.slice(0, start) + text + body.slice(end);
    setBody(newBody);
    setShowVarPicker(false);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + text.length, start + text.length);
    }, 0);
  };

  const handleRefine = async (action: string) => {
    setRefining(true);
    try {
      const { data } = await api.post<{ subject: string | null; body: string }>("/templates/refine", {
        current_subject: subject || null,
        current_body: body,
        action,
        channel: template?.channel || "email",
      });
      if (data.subject !== null && template?.channel === "email") setSubject(data.subject);
      setBody(data.body);
      toast.success(`Applied: ${action}`);
    } catch (err) { toast.error(getErrorMessage(err, "Refine failed")); }
    setRefining(false);
  };

  // Preview: replace {{var}} with example values
  const previewText = (text: string) => {
    return text.replace(/\{\{([a-z_][a-z0-9_.]*)\}\}/g, (_, key) => {
      const v = variables.find((v) => v.key === key);
      return v ? v.example : `{{${key}}}`;
    });
  };

  if (loading) {
    return <AppShell title="Template"><FullWidthLayout><Skeleton variant="card" className="h-32 mb-4" /><Skeleton variant="card" className="h-64" /></FullWidthLayout></AppShell>;
  }

  if (!template) {
    return <AppShell title="Template"><FullWidthLayout><p className="text-sm text-text-secondary">Template not found</p></FullWidthLayout></AppShell>;
  }

  return (
    <AppShell title={template.name}>
      <FullWidthLayout>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/settings/templates")} className="text-text-tertiary hover:text-text-primary cursor-pointer">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{name || "Untitled"}</h2>
                {template.channel === "email" ? <EnvelopeSimple className="h-5 w-5 text-primary" /> : <WhatsappLogo className="h-5 w-5 text-whatsapp" />}
                <Badge size="sm" variant="outline">{CATEGORY_LABELS[category] || category}</Badge>
                {template.ai_generated && <Badge size="sm" variant="outline"><Sparkle className="h-3 w-3 mr-0.5" /> AI</Badge>}
              </div>
              <p className="text-xs text-text-tertiary mt-0.5">
                Created {formatRelativeTime(template.created_at)} · Used {template.usage_count}x
              </p>
            </div>
          </div>
          <Button onClick={handleSave} isLoading={saving}>
            <FloppyDisk className="h-4 w-4 mr-1" /> Save
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Left: Editor (3/5) */}
          <div className="lg:col-span-3 space-y-4">
            <Card>
              <div className="space-y-4">
                <Input label="Template Name" value={name} onChange={(e) => setName(e.target.value)} />

                <div>
                  <p className="text-[13px] font-medium text-text-primary mb-1.5">Category</p>
                  <div className="flex flex-wrap gap-1.5">
                    {CATEGORIES.map((cat) => (
                      <button key={cat} onClick={() => setCategory(cat)}
                        className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                          category === cat ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                        }`}>{CATEGORY_LABELS[cat]}</button>
                    ))}
                  </div>
                </div>

                {template.channel === "email" && (
                  <Input label="Subject Line" placeholder="e.g. {{product}} from {{tenant_company}} — FOB prices" value={subject} onChange={(e) => setSubject(e.target.value)} />
                )}

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[13px] font-medium text-text-primary">Body</p>
                    <div className="flex items-center gap-1">
                      <div className="relative">
                        <button onClick={() => setShowVarPicker(!showVarPicker)}
                          className="px-2 py-1 rounded-[var(--radius-sm)] text-xs border border-border text-text-secondary hover:border-primary/30 hover:text-primary transition-colors cursor-pointer flex items-center gap-1">
                          <Hash className="h-3.5 w-3.5" /> Insert Variable
                        </button>
                        {showVarPicker && (
                          <div className="absolute right-0 top-8 z-20 w-64 rounded-[var(--radius-md)] border border-border bg-surface shadow-[var(--shadow-lg)] max-h-[250px] overflow-y-auto py-1">
                            {variables.map((v) => (
                              <button key={v.key} onClick={() => insertVariable(v.key)}
                                className="w-full text-left px-3 py-1.5 hover:bg-border-light transition-colors cursor-pointer">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-mono text-primary">{`{{${v.key}}}`}</span>
                                  <span className="text-[10px] text-text-tertiary">{v.example}</span>
                                </div>
                                <p className="text-[10px] text-text-secondary">{v.description}</p>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  <textarea
                    ref={bodyRef}
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={template.channel === "whatsapp" ? 6 : 12}
                    className="w-full px-3 py-2 border border-border rounded-[var(--radius-sm)] text-sm bg-surface text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/20 font-mono resize-y"
                    placeholder="Write your message template here. Use {{variable_name}} for dynamic content..."
                  />
                  {template.channel === "whatsapp" && (
                    <p className={`text-[10px] mt-1 ${body.length > 300 ? "text-error" : "text-text-tertiary"}`}>
                      {body.length}/300 characters
                    </p>
                  )}
                </div>

                <Input label="Description (optional)" placeholder="Internal note about when to use this template" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
            </Card>

            {/* AI Refine buttons */}
            <Card>
              <p className="text-xs font-semibold text-text-primary mb-2 flex items-center gap-1">
                <Sparkle className="h-3.5 w-3.5 text-warning" /> AI Refine
              </p>
              <div className="flex flex-wrap gap-2">
                {[
                  { action: "shorter", label: "Shorter", icon: ArrowsInSimple },
                  { action: "longer", label: "Longer", icon: ArrowsOutSimple },
                  { action: "formal", label: "More Formal", icon: TextAa },
                  { action: "friendly", label: "More Friendly", icon: HandWaving },
                  { action: "add_cta", label: "Add CTA", icon: Megaphone },
                ].map(({ action, label, icon: Icon }) => (
                  <button key={action} onClick={() => handleRefine(action)} disabled={refining || !body.trim()}
                    className="px-3 py-1.5 rounded-[var(--radius-sm)] text-xs border border-border text-text-secondary hover:border-primary/30 hover:text-primary transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50">
                    <Icon className="h-3.5 w-3.5" /> {label}
                  </button>
                ))}
                {refining && <span className="text-xs text-text-tertiary animate-pulse">Refining...</span>}
              </div>
            </Card>
          </div>

          {/* Right: Preview (2/5) */}
          <div className="lg:col-span-2">
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <button onClick={() => setPreviewMode(false)}
                  className={`px-3 py-1 rounded-[var(--radius-sm)] text-xs transition-colors cursor-pointer flex items-center gap-1 ${!previewMode ? "bg-primary/10 text-primary font-medium" : "text-text-secondary hover:text-text-primary"}`}>
                  <Code className="h-3.5 w-3.5" /> Raw
                </button>
                <button onClick={() => setPreviewMode(true)}
                  className={`px-3 py-1 rounded-[var(--radius-sm)] text-xs transition-colors cursor-pointer flex items-center gap-1 ${previewMode ? "bg-primary/10 text-primary font-medium" : "text-text-secondary hover:text-text-primary"}`}>
                  <Eye className="h-3.5 w-3.5" /> Preview
                </button>
              </div>

              {template.channel === "email" && (subject || previewMode) && (
                <div className="mb-3 pb-3 border-b border-border">
                  <p className="text-[10px] text-text-tertiary uppercase tracking-wide mb-0.5">Subject</p>
                  <p className="text-sm font-medium text-text-primary">
                    {previewMode ? previewText(subject) : subject || "(no subject)"}
                  </p>
                </div>
              )}

              <div>
                <p className="text-[10px] text-text-tertiary uppercase tracking-wide mb-1">Body</p>
                <div className={`text-sm text-text-primary whitespace-pre-wrap ${template.channel === "whatsapp" ? "bg-green-50 dark:bg-green-950/20 rounded-[var(--radius-md)] p-3 border border-green-200 dark:border-green-900" : ""}`}>
                  {previewMode ? previewText(body) : body || "(empty)"}
                </div>
              </div>

              {/* Detected variables */}
              {template.variables.length > 0 && (
                <div className="mt-4 pt-3 border-t border-border">
                  <p className="text-[10px] text-text-tertiary uppercase tracking-wide mb-1.5">Variables Used</p>
                  <div className="flex flex-wrap gap-1.5">
                    {template.variables.map((v) => (
                      <span key={v} className="text-[10px] px-1.5 py-0.5 rounded bg-info/10 text-info font-mono">{`{{${v}}}`}</span>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </FullWidthLayout>
    </AppShell>
  );
}
