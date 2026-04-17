"use client";
import type { TemplateVariable } from "@/types";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import {
  ArrowLeft, Sparkle, EnvelopeSimple, WhatsappLogo, ArrowRight,
  ArrowClockwise,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";

const CATEGORIES = [
  { key: "introduction", label: "Introduction", desc: "First contact with a new buyer" },
  { key: "price_update", label: "Price Update", desc: "Share current pricing" },
  { key: "follow_up", label: "Follow Up", desc: "Follow up on a previous message" },
  { key: "sample_offer", label: "Sample Offer", desc: "Offer product samples" },
  { key: "festive_greeting", label: "Festive Greeting", desc: "Holiday/seasonal greeting" },
  { key: "reactivation", label: "Reactivation", desc: "Re-engage dormant contacts" },
  { key: "custom", label: "Custom", desc: "Your own message type" },
];

const TONES = [
  { key: "professional", label: "Professional" },
  { key: "friendly", label: "Friendly" },
  { key: "direct", label: "Direct" },
  { key: "festive", label: "Festive" },
];

export default function NewTemplatePage() {
  const router = useRouter();

  // Step 1: Config
  const [channel, setChannel] = useState<string>("email");
  const [category, setCategory] = useState<string>("introduction");
  const [tone, setTone] = useState<string>("professional");

  // Step 2: Context + Variables
  const [context, setContext] = useState("");
  const [allVars, setAllVars] = useState<TemplateVariable[]>([]);
  const [selectedVars, setSelectedVars] = useState<string[]>(["contact_first_name", "company_name", "product", "tenant_company"]);

  // Step 3: Result
  const [generating, setGenerating] = useState(false);
  const [resultSubject, setResultSubject] = useState("");
  const [resultBody, setResultBody] = useState("");
  const [generated, setGenerated] = useState(false);
  const [saving, setSaving] = useState(false);

  const [step, setStep] = useState(1);

  useEffect(() => {
    api.get<TemplateVariable[]>("/templates/variables").then(({ data }) => setAllVars(data)).catch(() => {});
  }, []);

  // Pre-tick variables based on category
  useEffect(() => {
    const presets: Record<string, string[]> = {
      introduction: ["contact_first_name", "company_name", "product", "tenant_company"],
      price_update: ["contact_first_name", "product", "fob_price", "tenant_company"],
      follow_up: ["contact_first_name", "company_name", "product"],
      sample_offer: ["contact_first_name", "product", "company_name"],
      festive_greeting: ["contact_first_name", "tenant_company", "season"],
      reactivation: ["contact_first_name", "company_name", "product", "tenant_company"],
      custom: ["contact_first_name", "company_name"],
    };
    setSelectedVars(presets[category] || presets.custom);
  }, [category]);

  const toggleVar = (key: string) => {
    setSelectedVars((prev) => prev.includes(key) ? prev.filter((v) => v !== key) : [...prev, key]);
  };

  const handleGenerate = async () => {
    if (!context.trim()) { toast.error("Please describe your message"); return; }
    setGenerating(true);
    try {
      const { data } = await api.post<{ subject: string | null; body: string; variables_detected: string[] }>("/templates/generate", {
        channel, category, tone, context: context.trim(), variables_hint: selectedVars,
      });
      setResultSubject(data.subject || "");
      setResultBody(data.body);
      setGenerated(true);
      setStep(3);
    } catch (err) { toast.error(getErrorMessage(err, "Generation failed")); }
    setGenerating(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const { data } = await api.post<{ id: string }>("/templates", {
        name: `${category.replace(/_/g, " ")} — ${channel}`.replace(/\b\w/g, (l) => l.toUpperCase()),
        channel, category,
        subject: channel === "email" ? resultSubject || null : null,
        body: resultBody,
        ai_generated: true,
        ai_prompt: context,
      });
      toast.success("Template saved to library");
      router.push(`/settings/templates/${data.id}`);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to save")); }
    setSaving(false);
  };

  return (
    <AppShell title="New Template">
      <FullWidthLayout>
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.push("/settings/templates")} className="text-text-tertiary hover:text-text-primary cursor-pointer">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary flex items-center gap-2">
              <Sparkle className="h-5 w-5 text-warning" /> Generate Template with AI
            </h2>
            <p className="text-sm text-text-secondary">Step {step} of 3</p>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((s) => (
            <div key={s} className={`h-1.5 flex-1 rounded-full transition-colors ${s <= step ? "bg-primary" : "bg-border"}`} />
          ))}
        </div>

        {/* Step 1: Channel + Category + Tone */}
        {step === 1 && (
          <Card>
            <div className="space-y-6">
              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Channel</p>
                <div className="flex gap-3">
                  <button onClick={() => setChannel("email")}
                    className={`flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] border-2 transition-all cursor-pointer ${channel === "email" ? "border-primary bg-primary/5" : "border-border hover:border-primary/30"}`}>
                    <EnvelopeSimple className="h-5 w-5 text-primary" /> <span className="text-sm font-medium">Email</span>
                  </button>
                  <button onClick={() => setChannel("whatsapp")}
                    className={`flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] border-2 transition-all cursor-pointer ${channel === "whatsapp" ? "border-whatsapp bg-green-50" : "border-border hover:border-green-300"}`}>
                    <WhatsappLogo className="h-5 w-5 text-whatsapp" /> <span className="text-sm font-medium">WhatsApp</span>
                  </button>
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Category</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {CATEGORIES.map((cat) => (
                    <button key={cat.key} onClick={() => setCategory(cat.key)}
                      className={`text-left px-3 py-2 rounded-[var(--radius-md)] border transition-all cursor-pointer ${category === cat.key ? "border-primary bg-primary/5" : "border-border hover:border-primary/30"}`}>
                      <p className="text-sm font-medium text-text-primary">{cat.label}</p>
                      <p className="text-[10px] text-text-tertiary">{cat.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {channel === "email" && (
                <div>
                  <p className="text-sm font-semibold text-text-primary mb-2">Tone</p>
                  <div className="flex gap-2">
                    {TONES.map((t) => (
                      <button key={t.key} onClick={() => setTone(t.key)}
                        className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                          tone === t.key ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                        }`}>{t.label}</button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <Button onClick={() => setStep(2)}>
                  Next <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Step 2: Context + Variables */}
        {step === 2 && (
          <Card>
            <div className="space-y-6">
              <div>
                <p className="text-sm font-semibold text-text-primary mb-1">Describe your message in one line</p>
                <p className="text-xs text-text-tertiary mb-2">e.g. &quot;Introducing ourselves as premium black pepper exporters from Kerala to Middle East buyers.&quot;</p>
                <Textarea
                  value={context} onChange={(e) => setContext(e.target.value)}
                  rows={3} placeholder="What should this message say?"
                  autoFocus
                />
              </div>

              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Variables to include</p>
                <div className="flex flex-wrap gap-2">
                  {allVars.map((v) => (
                    <button key={v.key} onClick={() => toggleVar(v.key)}
                      className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs font-mono border transition-colors cursor-pointer ${
                        selectedVars.includes(v.key) ? "bg-info/10 text-info border-info/30" : "bg-surface text-text-tertiary border-border"
                      }`}>{`{{${v.key}}}`}</button>
                  ))}
                </div>
              </div>

              <div className="flex justify-between">
                <Button variant="secondary" onClick={() => setStep(1)}>
                  <ArrowLeft className="h-4 w-4 mr-1" /> Back
                </Button>
                <Button onClick={handleGenerate} isLoading={generating}>
                  <Sparkle className="h-4 w-4 mr-1" /> Generate
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Step 3: Result */}
        {step === 3 && generated && (
          <Card>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                  <Sparkle className="h-4 w-4 text-warning" /> Generated Template
                </p>
                <div className="flex items-center gap-1.5">
                  <Badge size="sm" variant="outline">{channel}</Badge>
                  <Badge size="sm" variant="outline">{category.replace(/_/g, " ")}</Badge>
                </div>
              </div>

              {channel === "email" && (
                <div>
                  <p className="text-[10px] text-text-tertiary uppercase tracking-wide mb-0.5">Subject</p>
                  <Input value={resultSubject} onChange={(e) => setResultSubject(e.target.value)} />
                </div>
              )}

              <div>
                <p className="text-[10px] text-text-tertiary uppercase tracking-wide mb-0.5">Body</p>
                <textarea
                  value={resultBody} onChange={(e) => setResultBody(e.target.value)}
                  rows={channel === "whatsapp" ? 6 : 12}
                  className="w-full px-3 py-2 border border-border rounded-[var(--radius-sm)] text-sm bg-surface text-text-primary font-mono resize-y focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="flex justify-between">
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setStep(2)}>
                    <ArrowLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                  <Button variant="secondary" onClick={handleGenerate} isLoading={generating}>
                    <ArrowClockwise className="h-4 w-4 mr-1" /> Regenerate
                  </Button>
                </div>
                <Button onClick={handleSave} isLoading={saving}>
                  Save to Library
                </Button>
              </div>
            </div>
          </Card>
        )}
      </FullWidthLayout>
    </AppShell>
  );
}
