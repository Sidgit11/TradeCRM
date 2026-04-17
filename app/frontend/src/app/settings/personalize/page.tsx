"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { SettingsNav } from "@/components/layout/SettingsNav";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Check, FunnelSimple, ChatText, Package, Star, Sliders,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";

interface Preferences {
  ignore_below_qty_mt: number | null;
  ignore_countries: string[];
  auto_non_lead_if_no_catalog_match: boolean;
  reply_tone: string;
  reply_language: string;
  include_fob_price: boolean;
  include_cfr_quote: boolean;
  include_certifications: boolean;
  include_moq: boolean;
  high_value_threshold_mt: number | null;
  high_value_reply_style: string | null;
  custom_reply_instructions: string | null;
  _is_default?: boolean;
}

export default function PersonalizePage() {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [saving, setSaving] = useState(false);
  const [step, setStep] = useState(0);
  const [ignoreCountriesText, setIgnoreCountriesText] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Preferences>("/leads/preferences/current");
        setPrefs(data);
        setIgnoreCountriesText((data.ignore_countries || []).join(", "));
      } catch { toast.error("Failed to load preferences"); }
    })();
  }, []);

  const updatePref = <K extends keyof Preferences>(key: K, value: Preferences[K]) => {
    if (prefs) setPrefs({ ...prefs, [key]: value });
  };

  const handleSave = async () => {
    if (!prefs) return;
    setSaving(true);
    try {
      await api.put("/leads/preferences/current", {
        ignore_below_qty_mt: prefs.ignore_below_qty_mt,
        ignore_countries: ignoreCountriesText ? ignoreCountriesText.split(",").map((s: string) => s.trim()).filter(Boolean) : [],
        auto_non_lead_if_no_catalog_match: prefs.auto_non_lead_if_no_catalog_match,
        reply_tone: prefs.reply_tone,
        reply_language: prefs.reply_language,
        include_fob_price: prefs.include_fob_price,
        include_cfr_quote: prefs.include_cfr_quote,
        include_certifications: prefs.include_certifications,
        include_moq: prefs.include_moq,
        high_value_threshold_mt: prefs.high_value_threshold_mt,
        high_value_reply_style: prefs.high_value_reply_style,
        custom_reply_instructions: prefs.custom_reply_instructions,
      });
      toast.success("Preferences saved");
    } catch (err) { toast.error(getErrorMessage(err, "Failed to save preferences")); }
    setSaving(false);
  };

  if (!prefs) return <AppShell title="Settings"><FullWidthLayout><SettingsNav /><p className="text-sm text-text-tertiary">Loading...</p></FullWidthLayout></AppShell>;

  const steps = [
    { title: "What should we ignore?", icon: FunnelSimple },
    { title: "How should we reply?", icon: ChatText },
    { title: "What to include in replies?", icon: Package },
    { title: "High-value inquiries", icon: Star },
    { title: "Custom AI instructions", icon: Sliders },
  ];

  return (
    <AppShell title="Settings">
      <FullWidthLayout>
        <SettingsNav />

        <div className="max-w-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Personalize AI Behavior</h2>
              <p className="text-sm text-text-secondary mt-0.5">
                Configure how the AI classifies leads and drafts replies.
                {prefs._is_default && <Badge size="sm" variant="outline" className="ml-2">Using defaults</Badge>}
              </p>
            </div>
            <Button onClick={handleSave} isLoading={saving}>
              <Check className="h-4 w-4 mr-1" /> Save Preferences
            </Button>
          </div>

          {/* Step indicators */}
          <div className="flex gap-1 mb-6">
            {steps.map((s, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={`flex-1 flex items-center gap-1.5 px-3 py-2 rounded-[var(--radius-sm)] text-xs font-medium transition-colors cursor-pointer ${
                  step === i ? "bg-primary text-text-inverse" : "bg-border-light text-text-secondary hover:bg-border"
                }`}
              >
                <s.icon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{s.title}</span>
                <span className="sm:hidden">{i + 1}</span>
              </button>
            ))}
          </div>

          {/* Step 1: Filtering */}
          {step === 0 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">What should we ignore?</h3>
              <div className="space-y-5">
                <div>
                  <Input
                    label="Minimum quantity threshold (MT)"
                    placeholder="e.g. 1"
                    value={prefs.ignore_below_qty_mt?.toString() || ""}
                    onChange={(e) => updatePref("ignore_below_qty_mt", e.target.value ? parseFloat(e.target.value) : null)}
                    helperText="Inquiries below this quantity will be auto-classified as non-lead"
                  />
                </div>
                <div>
                  <Input
                    label="Ignore countries (comma-separated)"
                    placeholder="e.g. North Korea, Iran"
                    value={ignoreCountriesText}
                    onChange={(e) => setIgnoreCountriesText(e.target.value)}
                    helperText="Inquiries from these countries will be auto-dismissed"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Auto-dismiss if product not in catalog</p>
                    <p className="text-xs text-text-secondary">If the requested product doesn't match your catalog, mark as non-lead</p>
                  </div>
                  <button
                    onClick={() => updatePref("auto_non_lead_if_no_catalog_match", !prefs.auto_non_lead_if_no_catalog_match)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${prefs.auto_non_lead_if_no_catalog_match ? "bg-primary" : "bg-border"}`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-surface shadow-sm transition-transform ${prefs.auto_non_lead_if_no_catalog_match ? "translate-x-5.5" : "translate-x-0.5"}`} />
                  </button>
                </div>
              </div>
              <div className="flex justify-end mt-6">
                <Button onClick={() => setStep(1)}>Next</Button>
              </div>
            </Card>
          )}

          {/* Step 2: Reply tone */}
          {step === 1 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">How should we reply?</h3>
              <div className="space-y-5">
                <div>
                  <p className="text-sm font-medium text-text-primary mb-2">Reply tone</p>
                  <div className="flex gap-2">
                    {["formal", "friendly", "brief"].map((tone) => (
                      <button
                        key={tone}
                        onClick={() => updatePref("reply_tone", tone)}
                        className={`px-4 py-2 rounded-[var(--radius-sm)] text-sm border transition-colors cursor-pointer ${
                          prefs.reply_tone === tone
                            ? "bg-primary text-text-inverse border-primary"
                            : "bg-surface text-text-secondary border-border hover:border-primary-lighter"
                        }`}
                      >
                        {tone.charAt(0).toUpperCase() + tone.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary mb-2">Reply language</p>
                  <div className="flex gap-2">
                    {[
                      { value: "match_sender", label: "Match sender's language" },
                      { value: "english", label: "Always English" },
                    ].map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => updatePref("reply_language", opt.value)}
                        className={`px-4 py-2 rounded-[var(--radius-sm)] text-sm border transition-colors cursor-pointer ${
                          prefs.reply_language === opt.value
                            ? "bg-primary text-text-inverse border-primary"
                            : "bg-surface text-text-secondary border-border hover:border-primary-lighter"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex justify-between mt-6">
                <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                <Button onClick={() => setStep(2)}>Next</Button>
              </div>
            </Card>
          )}

          {/* Step 3: Reply content */}
          {step === 2 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">What to include in replies?</h3>
              <div className="space-y-4">
                {[
                  { key: "include_fob_price" as const, label: "Current FOB price from your catalog", desc: "Include today's FOB price for the requested product" },
                  { key: "include_cfr_quote" as const, label: "CFR estimate (if buyer mentions destination)", desc: "Auto-calculate CFR using your freight rates" },
                  { key: "include_certifications" as const, label: "Your certifications", desc: "Mention FSSAI, Organic, Fair Trade etc. from your product catalog" },
                  { key: "include_moq" as const, label: "Minimum order quantity", desc: "Include MOQ from your product grade specifications" },
                ].map((item) => (
                  <div key={item.key} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-text-primary">{item.label}</p>
                      <p className="text-xs text-text-secondary">{item.desc}</p>
                    </div>
                    <button
                      onClick={() => updatePref(item.key, !prefs[item.key])}
                      className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${prefs[item.key] ? "bg-primary" : "bg-border"}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-surface shadow-sm transition-transform ${prefs[item.key] ? "translate-x-5.5" : "translate-x-0.5"}`} />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-6">
                <Button variant="ghost" onClick={() => setStep(1)}>Back</Button>
                <Button onClick={() => setStep(3)}>Next</Button>
              </div>
            </Card>
          )}

          {/* Step 4: High value */}
          {step === 3 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">High-value inquiries</h3>
              <div className="space-y-5">
                <Input
                  label="High-value threshold (MT)"
                  placeholder="e.g. 10"
                  value={prefs.high_value_threshold_mt?.toString() || ""}
                  onChange={(e) => updatePref("high_value_threshold_mt", e.target.value ? parseFloat(e.target.value) : null)}
                  helperText="Inquiries above this quantity get special treatment"
                />
                <Textarea
                  label="Special treatment for high-value leads"
                  placeholder="e.g. Prioritize response, offer samples, mention bulk discount, assign to senior team member..."
                  value={prefs.high_value_reply_style || ""}
                  onChange={(e) => updatePref("high_value_reply_style", e.target.value || null)}
                  helperText="Instructions for the AI when replying to high-value inquiries"
                />
              </div>
              <div className="flex justify-between mt-6">
                <Button variant="ghost" onClick={() => setStep(2)}>Back</Button>
                <Button onClick={() => setStep(4)}>Next</Button>
              </div>
            </Card>
          )}

          {/* Step 5: Custom instructions */}
          {step === 4 && (
            <Card>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] mb-4">Custom AI instructions</h3>
              <Textarea
                label="Any other rules for the AI?"
                placeholder={"e.g.\n- Always mention we ship within 7 days of LC receipt\n- Never mention competitor names\n- For orders above 50MT, offer 2% discount\n- Always mention we are FSSAI and ISO certified"}
                value={prefs.custom_reply_instructions || ""}
                onChange={(e) => updatePref("custom_reply_instructions", e.target.value || null)}
                helperText="These instructions are passed directly to the AI when classifying emails and drafting replies"
                className="min-h-[150px]"
              />
              <div className="flex justify-between mt-6">
                <Button variant="ghost" onClick={() => setStep(3)}>Back</Button>
                <Button onClick={handleSave} isLoading={saving}>
                  <Check className="h-4 w-4 mr-1" /> Save All Preferences
                </Button>
              </div>
            </Card>
          )}
        </div>
      </FullWidthLayout>
    </AppShell>
  );
}
