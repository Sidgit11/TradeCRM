"use client";
import type { Company } from "@/types";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Buildings, Plus, Globe, MapPin, Phone, EnvelopeSimple,
  DotsThreeVertical, PencilSimple, Trash,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { ProductPicker } from "@/components/ui/ProductPicker";
import { toast } from "sonner";
import { formatRelativeTime, formatNumber } from "@/lib/utils";


const COMPANY_TYPES = ["importer", "distributor", "manufacturer", "broker", "retailer", "agent", "re-exporter", "end_user", "other"];

export default function CompaniesPage() {
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");

  // Only essential fields for quick creation
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [companyType, setCompanyType] = useState("");
  const [commodities, setCommodities] = useState<string[]>([]);
  const [rating, setRating] = useState("");
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = () => setMenuOpen(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [menuOpen]);

  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Company[]; total: number }>(
        `/companies?limit=50${search ? `&search=${encodeURIComponent(search)}` : ""}`
      );
      setCompanies(data.items);
      setTotal(data.total);
    } catch { toast.error("Failed to load companies"); }
    setLoading(false);
  }, [search]);

  useEffect(() => { fetchCompanies(); }, [fetchCompanies]);

  const resetAddForm = () => { setName(""); setCountry(""); setCompanyType(""); setCommodities([]); setRating(""); };

  const handleCreate = async () => {
    if (!name.trim() || !country.trim()) { toast.error("Name and country are required"); return; }
    setSaving(true);
    try {
      await api.post("/companies", {
        name: name.trim(),
        country: country.trim(),
        company_type: companyType || undefined,
        commodities: commodities,
        rating: rating || undefined,
      });
      toast.success("Company created");
      setShowAdd(false); resetAddForm();
      fetchCompanies();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create company")); }
    setSaving(false);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    setDeleting(id);
    try {
      await api.delete(`/companies/${id}`);
      toast.success(`"${name}" deleted`);
      fetchCompanies();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to delete company")); }
    setDeleting(null);
    setMenuOpen(null);
  };

  return (
    <AppShell title="Companies">
      <FullWidthLayout>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Companies</h2>
            {total > 0 && <p className="text-sm text-text-secondary">{total} companies</p>}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => router.push("/discover")}>Discover Buyers</Button>
            <Button onClick={() => setShowAdd(true)}><Plus className="h-4 w-4 mr-1" /> Add Company</Button>
          </div>
        </div>

        <div className="mb-4">
          <Input type="search" inputSize="sm" placeholder="Search companies..." value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchCompanies()}
          />
        </div>

        {loading ? (
          <div className="space-y-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} variant="card" className="h-16" />)}</div>
        ) : companies.length === 0 ? (
          <EmptyState
            icon={<Buildings className="h-12 w-12" />}
            heading="No companies yet"
            description="Companies from leads or manual entry will appear here."
            actionLabel="Add Company"
            onAction={() => setShowAdd(true)}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {companies.map((c) => (
              <div key={c.id} className="rounded-[var(--radius-md)] border border-border bg-surface p-4 hover:shadow-[var(--shadow-md)] transition-shadow cursor-pointer"
                onClick={() => router.push(`/companies/${c.id}`)}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-text-primary truncate">{c.name}</h3>
                    {c.company_type && <span className="text-[10px] text-text-tertiary capitalize">{c.company_type}</span>}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {c.rating && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                        c.rating === "hot" ? "bg-error/10 text-red-700" :
                        c.rating === "warm" ? "bg-warning/10 text-amber-700" : "bg-info/10 text-blue-700"
                      }`}>{c.rating}</span>
                    )}
                    <Badge size="sm" variant="outline">{c.source}</Badge>
                    <div className="relative">
                      <button onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === c.id ? null : c.id); }}
                        className="p-1 rounded-[var(--radius-sm)] hover:bg-border-light text-text-tertiary hover:text-text-primary transition-colors cursor-pointer">
                        <DotsThreeVertical className="h-4 w-4" weight="bold" />
                      </button>
                      {menuOpen === c.id && (
                        <div className="absolute right-0 top-8 z-10 w-36 rounded-[var(--radius-md)] border border-border bg-surface shadow-[var(--shadow-lg)] py-1"
                          onClick={(e) => e.stopPropagation()}>
                          <button onClick={() => { setMenuOpen(null); router.push(`/companies/${c.id}`); }}
                            className="w-full text-left px-3 py-1.5 text-sm text-text-secondary hover:bg-border-light flex items-center gap-2 cursor-pointer">
                            <PencilSimple className="h-3.5 w-3.5" /> Edit
                          </button>
                          <button onClick={() => handleDelete(c.id, c.name)}
                            disabled={deleting === c.id}
                            className="w-full text-left px-3 py-1.5 text-sm text-error hover:bg-error/5 flex items-center gap-2 cursor-pointer disabled:opacity-50">
                            <Trash className="h-3.5 w-3.5" /> {deleting === c.id ? "Deleting..." : "Delete"}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="space-y-1 mb-2">
                  {c.country && (
                    <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                      <MapPin className="h-3 w-3 shrink-0" /> {[c.city, c.state, c.country].filter(Boolean).join(", ")}
                    </div>
                  )}
                  {(c.phone || c.email) && (
                    <div className="flex items-center gap-3 text-xs text-text-secondary">
                      {c.phone && <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {c.phone}</span>}
                      {c.email && <span className="flex items-center gap-1"><EnvelopeSimple className="h-3 w-3" /> {c.email}</span>}
                    </div>
                  )}
                  {c.website && (
                    <div className="flex items-center gap-1.5 text-xs text-text-tertiary">
                      <Globe className="h-3 w-3" /> {c.website}
                    </div>
                  )}
                </div>

                {c.commodities.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {c.commodities.slice(0, 3).map((com) => <Badge key={com} size="sm">{com}</Badge>)}
                    {c.commodities.length > 3 && <Badge size="sm" variant="outline">+{c.commodities.length - 3}</Badge>}
                  </div>
                )}

                <div className="flex items-center justify-between text-[10px] text-text-tertiary pt-2 border-t border-border">
                  <div className="flex gap-3">
                    {c.import_volume_annual != null && <span>{formatNumber(c.import_volume_annual)} MT/yr</span>}
                    {c.year_established && <span>Est. {c.year_established}</span>}
                    {c.total_inquiries > 0 && <span>{c.total_inquiries} inquiries</span>}
                    {c.total_deals_won > 0 && <span>{c.total_deals_won} deals</span>}
                  </div>
                  <span>{formatRelativeTime(c.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Company — single-step, only essentials */}
        <Modal open={showAdd} onOpenChange={(v) => { if (!v) { setShowAdd(false); resetAddForm(); } }}
          title="Add Company" size="md"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <Button variant="secondary" onClick={() => { setShowAdd(false); resetAddForm(); }}>Cancel</Button>
              <Button onClick={handleCreate} isLoading={saving}>Create Company</Button>
            </div>
          }
        >
          <div className="space-y-4">
            <Input label="Company Name *" placeholder="e.g. Euro Spice Trading BV" value={name} onChange={(e) => setName(e.target.value)} />
            <Input label="Country *" placeholder="e.g. Netherlands" value={country} onChange={(e) => setCountry(e.target.value)} />
            <div>
              <p className="text-[13px] font-medium text-text-primary mb-1.5">Company Type</p>
              <div className="flex flex-wrap gap-1.5">
                {COMPANY_TYPES.map((t) => (
                  <button key={t} onClick={() => setCompanyType(companyType === t ? "" : t)}
                    className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer capitalize ${
                      companyType === t ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border hover:border-primary-lighter"
                    }`}>{t}</button>
                ))}
              </div>
            </div>
            <ProductPicker label="Commodities They Buy" value={commodities} onChange={setCommodities} multi placeholder="Search your catalog..." />
            <div>
              <p className="text-[13px] font-medium text-text-primary mb-1.5">Rating</p>
              <div className="flex gap-2">
                {[{v: "hot", c: "bg-error/10 text-red-700 border-error/30"}, {v: "warm", c: "bg-warning/10 text-amber-700 border-warning/30"}, {v: "cold", c: "bg-info/10 text-blue-700 border-info/30"}].map(({v, c}) => (
                  <button key={v} onClick={() => setRating(rating === v ? "" : v)}
                    className={`px-3 py-1.5 rounded-[var(--radius-full)] text-xs border transition-colors cursor-pointer capitalize ${
                      rating === v ? c : "bg-surface text-text-secondary border-border"
                    }`}>{v}</button>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      </FullWidthLayout>
    </AppShell>
  );
}
