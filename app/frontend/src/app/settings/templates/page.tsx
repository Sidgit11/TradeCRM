"use client";
import type { MessageTemplate } from "@/types";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { SettingsNav } from "@/components/layout/SettingsNav";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  FileText, Plus, Sparkle, EnvelopeSimple, WhatsappLogo,
  DotsThreeVertical, PencilSimple, Copy, Trash, MagnifyingGlass,
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

export default function TemplatesLibraryPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [menuOpen, setMenuOpen] = useState<string | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = () => setMenuOpen(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [menuOpen]);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      let url = "/templates?";
      if (channelFilter !== "all") url += `channel=${channelFilter}&`;
      if (categoryFilter !== "all") url += `category=${categoryFilter}&`;
      const { data } = await api.get<MessageTemplate[]>(url);
      setTemplates(data);
    } catch { toast.error("Failed to load templates"); }
    setLoading(false);
  }, [channelFilter, categoryFilter]);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  const filtered = search.trim()
    ? templates.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()) || (t.description || "").toLowerCase().includes(search.toLowerCase()))
    : templates;

  const handleDuplicate = async (id: string) => {
    try {
      await api.post(`/templates/${id}/duplicate`, {});
      toast.success("Template duplicated");
      fetchTemplates();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to duplicate")); }
    setMenuOpen(null);
  };

  const handleArchive = async (id: string, name: string) => {
    if (!confirm(`Archive "${name}"?`)) return;
    try {
      await api.delete(`/templates/${id}`);
      toast.success("Template archived");
      fetchTemplates();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to archive")); }
    setMenuOpen(null);
  };

  return (
    <AppShell title="Settings">
      <FullWidthLayout>
        <SettingsNav />

        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Templates</h2>
            <p className="text-sm text-text-secondary">{templates.length} templates</p>
          </div>
          <Button onClick={() => router.push("/settings/templates/new")}>
            <Sparkle className="h-4 w-4 mr-1" /> New Template
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex gap-1">
            {[{ key: "all", label: "All" }, { key: "email", label: "Email" }, { key: "whatsapp", label: "WhatsApp" }].map(({ key, label }) => (
              <button key={key} onClick={() => setChannelFilter(key)}
                className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                  channelFilter === key ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                }`}>{label}</button>
            ))}
          </div>
          <div className="h-5 w-px bg-border" />
          <div className="flex gap-1 flex-wrap">
            <button onClick={() => setCategoryFilter("all")}
              className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                categoryFilter === "all" ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
              }`}>All</button>
            {CATEGORIES.map((cat) => (
              <button key={cat} onClick={() => setCategoryFilter(cat)}
                className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                  categoryFilter === cat ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
                }`}>{CATEGORY_LABELS[cat]}</button>
            ))}
          </div>
          <div className="flex-1" />
          <div className="w-56">
            <Input type="search" inputSize="sm" placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} variant="card" className="h-24" />)}</div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-12 w-12" />}
            heading="No templates yet"
            description="Create reusable message templates with AI. Type a one-liner, get a ready-to-use draft."
            actionLabel="Generate with AI"
            onAction={() => router.push("/settings/templates/new")}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map((t) => (
              <div key={t.id}
                className="rounded-[var(--radius-md)] border border-border bg-surface p-4 hover:shadow-[var(--shadow-md)] transition-shadow cursor-pointer"
                onClick={() => router.push(`/settings/templates/${t.id}`)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    {t.channel === "email" ? <EnvelopeSimple className="h-4 w-4 text-primary" /> : <WhatsappLogo className="h-4 w-4 text-whatsapp" />}
                    <Badge size="sm" variant="outline">{CATEGORY_LABELS[t.category] || t.category}</Badge>
                    {t.ai_generated && <Sparkle className="h-3 w-3 text-warning" />}
                  </div>
                  <div className="relative">
                    <button onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === t.id ? null : t.id); }}
                      className="p-1 rounded-[var(--radius-sm)] hover:bg-border-light text-text-tertiary hover:text-text-primary transition-colors cursor-pointer">
                      <DotsThreeVertical className="h-4 w-4" weight="bold" />
                    </button>
                    {menuOpen === t.id && (
                      <div className="absolute right-0 top-8 z-10 w-36 rounded-[var(--radius-md)] border border-border bg-surface shadow-[var(--shadow-lg)] py-1"
                        onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => { setMenuOpen(null); router.push(`/settings/templates/${t.id}`); }}
                          className="w-full text-left px-3 py-1.5 text-sm text-text-secondary hover:bg-border-light flex items-center gap-2 cursor-pointer">
                          <PencilSimple className="h-3.5 w-3.5" /> Edit
                        </button>
                        <button onClick={() => handleDuplicate(t.id)}
                          className="w-full text-left px-3 py-1.5 text-sm text-text-secondary hover:bg-border-light flex items-center gap-2 cursor-pointer">
                          <Copy className="h-3.5 w-3.5" /> Duplicate
                        </button>
                        <button onClick={() => handleArchive(t.id, t.name)}
                          className="w-full text-left px-3 py-1.5 text-sm text-error hover:bg-error/5 flex items-center gap-2 cursor-pointer">
                          <Trash className="h-3.5 w-3.5" /> Archive
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-text-primary mb-1 truncate">{t.name}</h3>
                {t.description && <p className="text-xs text-text-secondary mb-2 line-clamp-2">{t.description}</p>}

                {t.variables.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {t.variables.slice(0, 3).map((v) => (
                      <span key={v} className="text-[10px] px-1.5 py-0.5 rounded bg-info/10 text-info font-mono">{`{{${v}}}`}</span>
                    ))}
                    {t.variables.length > 3 && <span className="text-[10px] text-text-tertiary">+{t.variables.length - 3} more</span>}
                  </div>
                )}

                <div className="flex items-center justify-between text-[10px] text-text-tertiary pt-2 border-t border-border">
                  <span>{t.usage_count > 0 ? `Used ${t.usage_count}x` : "Not used yet"}</span>
                  <span>{t.last_used_at ? formatRelativeTime(t.last_used_at) : formatRelativeTime(t.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </FullWidthLayout>
    </AppShell>
  );
}
