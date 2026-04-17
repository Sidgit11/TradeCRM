"use client";
import type { Contact } from "@/types";

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
  AddressBook, Plus, UploadSimple, EnvelopeSimple, Phone, Buildings,
  WhatsappLogo, MapPin, ProhibitInset, DotsThreeVertical, PencilSimple, Trash,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime } from "@/lib/utils";


export default function ContactsPage() {
  const router = useRouter();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");

  // Only essential fields for quick creation
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = () => setMenuOpen(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [menuOpen]);

  const fetchContacts = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Contact[]; total: number }>(
        `/contacts?limit=50${search ? `&search=${encodeURIComponent(search)}` : ""}`
      );
      setContacts(data.items);
      setTotal(data.total);
    } catch { toast.error("Failed to load contacts"); }
    setLoading(false);
  }, [search]);

  useEffect(() => { fetchContacts(); }, [fetchContacts]);

  const resetAddForm = () => { setName(""); setEmail(""); setPhone(""); setCompany(""); setTitle(""); };

  const handleCreate = async () => {
    if (!name.trim()) { toast.error("Name is required"); return; }
    if (!email.trim() && !phone.trim()) { toast.error("Email or phone is required"); return; }
    setSaving(true);
    try {
      await api.post("/contacts", {
        name: name.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        company_name: company.trim() || undefined,
        title: title.trim() || undefined,
      });
      toast.success("Contact created");
      setShowAdd(false); resetAddForm();
      fetchContacts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create contact")); }
    setSaving(false);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    setDeleting(id);
    try {
      await api.delete(`/contacts/${id}`);
      toast.success(`"${name}" deleted`);
      fetchContacts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to delete contact")); }
    setDeleting(null);
    setMenuOpen(null);
  };

  return (
    <AppShell title="Contacts">
      <FullWidthLayout>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Contacts</h2>
            {total > 0 && <p className="text-sm text-text-secondary">{total} contacts</p>}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setShowImport(true)}>
              <UploadSimple className="h-4 w-4 mr-1" /> Import CSV
            </Button>
            <Button onClick={() => setShowAdd(true)}>
              <Plus className="h-4 w-4 mr-1" /> Add Contact
            </Button>
          </div>
        </div>

        <div className="mb-4">
          <Input type="search" inputSize="sm" placeholder="Search contacts..." value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchContacts()}
          />
        </div>

        {loading ? (
          <div className="space-y-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} variant="card" className="h-16" />)}</div>
        ) : contacts.length === 0 ? (
          <EmptyState
            icon={<AddressBook className="h-12 w-12" />}
            heading="No contacts yet"
            description="Import contacts from CSV or add them manually."
            actionLabel="Add First Contact"
            onAction={() => setShowAdd(true)}
          />
        ) : (
          <div className="space-y-1">
            {contacts.map((c) => (
              <div key={c.id}
                className="flex items-center justify-between p-3 rounded-[var(--radius-md)] border border-border bg-surface hover:shadow-[var(--shadow-sm)] transition-shadow cursor-pointer"
                onClick={() => router.push(`/contacts/${c.id}`)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {c.do_not_contact && <ProhibitInset className="h-3.5 w-3.5 text-error shrink-0" weight="fill" />}
                    <span className="text-sm font-medium text-text-primary">
                      {c.salutation ? `${c.salutation}. ` : ""}{c.name}
                    </span>
                    {c.title && <span className="text-xs text-text-tertiary">({c.title})</span>}
                    {c.is_decision_maker && <Badge size="sm" variant="success">DM</Badge>}
                    <Badge size="sm" variant="outline">{c.source}</Badge>
                  </div>
                  <div className="flex items-center gap-4 mt-0.5">
                    {c.company_name && (
                      <span className="flex items-center gap-1 text-xs text-text-secondary">
                        <Buildings className="h-3 w-3" /> {c.company_name}
                      </span>
                    )}
                    {(c.country || c.city) && (
                      <span className="flex items-center gap-1 text-xs text-text-secondary">
                        <MapPin className="h-3 w-3" /> {[c.city, c.country].filter(Boolean).join(", ")}
                      </span>
                    )}
                    {c.email && (
                      <span className="flex items-center gap-1 text-xs text-text-secondary">
                        <EnvelopeSimple className="h-3 w-3" /> {c.email}
                      </span>
                    )}
                    {c.phone && (
                      <span className="flex items-center gap-1 text-xs text-text-secondary">
                        <Phone className="h-3 w-3" /> {c.phone}
                        <a href={`https://wa.me/${c.phone.replace(/[^0-9]/g, "")}`} target="_blank" rel="noopener noreferrer"
                          className="text-whatsapp hover:text-green-600 ml-1" onClick={(e) => e.stopPropagation()}>
                          <WhatsappLogo className="h-3.5 w-3.5" weight="fill" />
                        </a>
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex flex-col items-end gap-0.5">
                    <span className="text-[10px] text-text-tertiary">{formatRelativeTime(c.created_at)}</span>
                    {c.total_interactions > 0 && (
                      <span className="text-[10px] text-text-tertiary">{c.total_interactions} interactions</span>
                    )}
                  </div>
                  <div className="relative">
                    <button onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === c.id ? null : c.id); }}
                      className="p-1 rounded-[var(--radius-sm)] hover:bg-border-light text-text-tertiary hover:text-text-primary transition-colors cursor-pointer">
                      <DotsThreeVertical className="h-4 w-4" weight="bold" />
                    </button>
                    {menuOpen === c.id && (
                      <div className="absolute right-0 top-8 z-10 w-36 rounded-[var(--radius-md)] border border-border bg-surface shadow-[var(--shadow-lg)] py-1"
                        onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => { setMenuOpen(null); router.push(`/contacts/${c.id}`); }}
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
            ))}
          </div>
        )}

        {/* Add Contact — single-step, only essentials */}
        <Modal open={showAdd} onOpenChange={(v) => { if (!v) { setShowAdd(false); resetAddForm(); } }}
          title="Add Contact" size="md"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <Button variant="secondary" onClick={() => { setShowAdd(false); resetAddForm(); }}>Cancel</Button>
              <Button onClick={handleCreate} isLoading={saving}>Create Contact</Button>
            </div>
          }
        >
          <div className="space-y-4">
            <Input label="Full Name *" placeholder="e.g. Hans Mueller" value={name} onChange={(e) => setName(e.target.value)} />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Email" type="email" placeholder="hans@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
              <Input label="Phone / WhatsApp" placeholder="+49 170 123 456" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <Input label="Company" placeholder="Company name" value={company} onChange={(e) => setCompany(e.target.value)} />
            <Input label="Designation / Title" placeholder="e.g. Head of Purchasing" value={title} onChange={(e) => setTitle(e.target.value)} />
            <p className="text-xs text-text-tertiary">You can add location, department, preferences and more details from the contact profile.</p>
          </div>
        </Modal>

        {/* Import Modal */}
        <Modal open={showImport} onOpenChange={setShowImport} title="Import Contacts from CSV" description="Upload a CSV with columns: name, email, phone, company, title, tags">
          <div className="py-4">
            <div className="border-2 border-dashed border-border rounded-[var(--radius-md)] p-8 text-center">
              <UploadSimple className="h-10 w-10 text-text-tertiary mx-auto mb-3" />
              <p className="text-sm text-text-secondary mb-1">Click to select your CSV file</p>
              <input type="file" accept=".csv" className="mt-3 text-sm" />
            </div>
          </div>
        </Modal>
      </FullWidthLayout>
    </AppShell>
  );
}
