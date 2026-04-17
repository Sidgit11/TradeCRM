"use client";
import type { PipelineOpportunity as Opportunity, PipelineStage as Stage, Company, Contact, Product } from "@/types";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import {
  Kanban, Buildings, User, Package, CurrencyDollar,
  CalendarBlank, Truck, TestTube, Plus, MagnifyingGlass,
  ArrowRight, ArrowLeft, Check, X,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { ProductPicker } from "@/components/ui/ProductPicker";
import { toast } from "sonner";
import { formatRelativeTime, formatNumber } from "@/lib/utils";
import {
  DndContext, DragOverlay, useDroppable, useDraggable,
  type DragStartEvent, type DragEndEvent, type DragOverEvent, PointerSensor, useSensor, useSensors,
} from "@dnd-kit/core";

// ─── Droppable Stage Column ──────────────────────────────────────────
function StageColumn({ stage, children, isOver }: { stage: Stage; children: React.ReactNode; isOver?: boolean }) {
  const { setNodeRef } = useDroppable({ id: stage.id });
  return (
    <div ref={setNodeRef} className={`w-[300px] shrink-0 transition-colors rounded-[var(--radius-md)] ${isOver ? "bg-primary/5 ring-2 ring-primary/20" : ""}`}>
      {children}
    </div>
  );
}

// ─── Draggable Opportunity Card ──────────────────────────────────────
function DraggableCard({ opp, onClick }: { opp: Opportunity; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: opp.id });

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={`rounded-[var(--radius-md)] border border-border bg-surface p-3 hover:shadow-[var(--shadow-md)] transition-shadow cursor-pointer ${isDragging ? "opacity-30" : ""}`}
    >
      <CardContent opp={opp} />
    </div>
  );
}

// ─── Card Content (shared between card and drag overlay) ─────────────
function CardContent({ opp }: { opp: Opportunity }) {
  return (
    <>
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-semibold text-text-primary truncate">{opp.title || "Untitled"}</p>
        {opp.display_id && <span className="text-[9px] text-text-tertiary font-mono shrink-0">{opp.display_id}</span>}
      </div>
      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-1.5 text-sm font-medium text-text-primary min-w-0">
          <Buildings className="h-3.5 w-3.5 text-text-tertiary shrink-0" />
          <span className="truncate">{opp.company_name || "Unknown Company"}</span>
        </div>
      </div>
      {opp.contact_name && (
        <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
          <User className="h-3 w-3 shrink-0" />
          {opp.contact_name}
        </div>
      )}
      {opp.commodity && (
        <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
          <Package className="h-3 w-3 shrink-0" />
          <span>{opp.commodity}</span>
          {opp.quantity_mt && <span className="text-text-tertiary">({opp.quantity_mt} MT)</span>}
        </div>
      )}
      {(opp.target_price || opp.our_price) && (
        <div className="flex items-center gap-2 text-xs mb-1">
          <CurrencyDollar className="h-3 w-3 text-text-tertiary shrink-0" />
          {opp.target_price && <span className="text-text-secondary">Target: ${formatNumber(opp.target_price)}</span>}
          {opp.our_price && <span className="text-success">Ours: ${formatNumber(opp.our_price)}</span>}
          {opp.competitor_price && <span className="text-error">Comp: ${formatNumber(opp.competitor_price)}</span>}
        </div>
      )}
      {(opp.incoterms || opp.payment_terms) && (
        <div className="flex items-center gap-2 text-[10px] text-text-tertiary mb-1">
          {opp.incoterms && <Badge size="sm" variant="outline">{opp.incoterms}</Badge>}
          {opp.payment_terms && <Badge size="sm" variant="outline">{opp.payment_terms}</Badge>}
        </div>
      )}
      {(opp.container_type || opp.target_shipment_date) && (
        <div className="flex items-center gap-2 text-[10px] text-text-tertiary mb-1">
          {opp.container_type && (
            <span className="flex items-center gap-0.5">
              <Truck className="h-3 w-3" />
              {opp.number_of_containers ? `${opp.number_of_containers}x ` : ""}{opp.container_type}
            </span>
          )}
          {opp.target_shipment_date && (
            <span className="flex items-center gap-0.5">
              <CalendarBlank className="h-3 w-3" />
              Ship: {opp.target_shipment_date}
            </span>
          )}
        </div>
      )}
      {opp.sample_sent && (
        <div className="flex items-center gap-1 text-[10px] mb-1">
          <TestTube className="h-3 w-3 text-text-tertiary" />
          <span className={opp.sample_approved === true ? "text-success" : opp.sample_approved === false ? "text-error" : "text-warning"}>
            Sample {opp.sample_approved === true ? "Approved" : opp.sample_approved === false ? "Rejected" : "Sent"}
          </span>
        </div>
      )}
      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-border">
        <div className="flex items-center gap-2">
          <Badge size="sm" variant="outline">{opp.source}</Badge>
          {opp.probability > 0 && <span className="text-[10px] text-text-tertiary">{opp.probability}%</span>}
        </div>
        <div className="flex items-center gap-2">
          {opp.follow_up_date && <span className="text-[10px] text-warning">Follow-up: {opp.follow_up_date}</span>}
          <span className="text-[10px] text-text-tertiary">{formatRelativeTime(opp.updated_at)}</span>
        </div>
      </div>
    </>
  );
}

// ─── Constants ────────────────────────────────────────────────────────
const INCOTERMS = ["FOB", "CFR", "CIF", "CnF", "EXW", "DDP"];
const PAYMENT_TERMS = ["LC at Sight", "TT Advance", "CAD", "DA", "Open Account", "LC 30 Days", "LC 60 Days", "LC 90 Days"];

// ─── Main Page ────────────────────────────────────────────────────────
export default function OpportunitiesPage() {
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [loading, setLoading] = useState(true);

  // DnD state
  const [activeOpp, setActiveOpp] = useState<Opportunity | null>(null);
  const [overStageId, setOverStageId] = useState<string | null>(null);

  // Create wizard state
  const [showCreate, setShowCreate] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [creating, setCreating] = useState(false);

  // Step 1: Company
  const [companySearch, setCompanySearch] = useState("");
  const [companyResults, setCompanyResults] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [creatingCompany, setCreatingCompany] = useState(false);

  // Step 2: Contact
  const [contactSearch, setContactSearch] = useState("");
  const [contactResults, setContactResults] = useState<Contact[]>([]);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [showNewContact, setShowNewContact] = useState(false);
  const [newContactName, setNewContactName] = useState("");
  const [newContactEmail, setNewContactEmail] = useState("");
  const [newContactPhone, setNewContactPhone] = useState("");
  const [creatingContact, setCreatingContact] = useState(false);

  // Step 3: Deal
  const [dealTitle, setDealTitle] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [productResults, setProductResults] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [dealCommodity, setDealCommodity] = useState("");
  const [dealQuantity, setDealQuantity] = useState("");
  const [dealTargetPrice, setDealTargetPrice] = useState("");
  const [dealIncoterms, setDealIncoterms] = useState("");
  const [dealPaymentTerms, setDealPaymentTerms] = useState("");
  const [dealNotes, setDealNotes] = useState("");

  const searchTimeout = useRef<ReturnType<typeof setTimeout>>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [oppsRes, stagesRes] = await Promise.all([
        api.get<Opportunity[]>("/pipeline"),
        api.get<Stage[]>("/pipeline/stages"),
      ]);
      setOpportunities(oppsRes.data);
      setStages(stagesRes.data);
    } catch { toast.error("Failed to load opportunities"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── DnD handlers ─────────────────────────────────────────────────
  function handleDragStart(event: DragStartEvent) {
    const opp = opportunities.find((o) => o.id === event.active.id);
    setActiveOpp(opp || null);
  }

  function handleDragOver(event: DragOverEvent) {
    setOverStageId(event.over?.id?.toString() || null);
  }

  async function handleDragEnd(event: DragEndEvent) {
    setActiveOpp(null);
    setOverStageId(null);

    const { active, over } = event;
    if (!over) return;

    const opp = opportunities.find((o) => o.id === active.id);
    if (!opp) return;

    const targetStageId = over.id.toString();
    if (opp.stage_id === targetStageId) return;

    // Optimistic update
    setOpportunities((prev) =>
      prev.map((o) => o.id === opp.id ? { ...o, stage_id: targetStageId, stage_name: stages.find((s) => s.id === targetStageId)?.name || o.stage_name, stage_color: stages.find((s) => s.id === targetStageId)?.color || o.stage_color } : o)
    );

    try {
      await api.put(`/pipeline/${opp.id}/move`, { stage_id: targetStageId });
      toast.success(`Moved to ${stages.find((s) => s.id === targetStageId)?.name}`);
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to move opportunity"));
      fetchData(); // revert
    }
  }

  // ── Company search ────────────────────────────────────────────────
  function searchCompanies(query: string) {
    setCompanySearch(query);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (!query.trim()) { setCompanyResults([]); return; }
    searchTimeout.current = setTimeout(async () => {
      try {
        const { data } = await api.get<{ items: Company[] }>(`/companies?search=${encodeURIComponent(query)}&limit=10`);
        setCompanyResults(data.items || []);
      } catch { setCompanyResults([]); }
    }, 200);
  }

  async function autoCreateCompany() {
    setCreatingCompany(true);
    try {
      const { data } = await api.post<Company>("/companies", { name: companySearch.trim(), source: "manual" });
      setSelectedCompany(data);
      setCompanySearch("");
      setCompanyResults([]);
      toast.success(`Company "${data.name}" created`);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create company")); }
    setCreatingCompany(false);
  }

  // ── Contact search ────────────────────────────────────────────────
  function searchContacts(query: string) {
    setContactSearch(query);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (!query.trim() && selectedCompany) {
      // Show all contacts for selected company
      searchTimeout.current = setTimeout(async () => {
        try {
          const { data } = await api.get<{ items: Contact[] }>(`/contacts?company=${encodeURIComponent(selectedCompany.name)}&limit=10`);
          setContactResults(data.items || []);
        } catch { setContactResults([]); }
      }, 100);
      return;
    }
    if (!query.trim()) { setContactResults([]); return; }
    searchTimeout.current = setTimeout(async () => {
      try {
        const companyFilter = selectedCompany ? `&company=${encodeURIComponent(selectedCompany.name)}` : "";
        const { data } = await api.get<{ items: Contact[] }>(`/contacts?search=${encodeURIComponent(query)}${companyFilter}&limit=10`);
        setContactResults(data.items || []);
      } catch { setContactResults([]); }
    }, 200);
  }

  async function createNewContact() {
    if (!newContactName.trim()) { toast.error("Contact name is required"); return; }
    setCreatingContact(true);
    try {
      const { data } = await api.post<Contact>("/contacts", {
        name: newContactName.trim(),
        email: newContactEmail.trim() || null,
        phone: newContactPhone.trim() || null,
        company_name: selectedCompany?.name || null,
        company_id: selectedCompany?.id || null,
        source: "manual",
      });
      setSelectedContact(data);
      setShowNewContact(false);
      setNewContactName(""); setNewContactEmail(""); setNewContactPhone("");
      toast.success(`Contact "${data.name}" created`);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create contact")); }
    setCreatingContact(false);
  }

  // ── Product search ────────────────────────────────────────────────
  function searchProducts(query: string) {
    setProductSearch(query);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(async () => {
      try {
        const { data } = await api.get<Product[]>("/catalog/products");
        const filtered = query.trim()
          ? data.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()))
          : data;
        setProductResults(filtered.slice(0, 10));
      } catch { setProductResults([]); }
    }, 200);
  }

  // ── Create opportunity ────────────────────────────────────────────
  async function handleCreate() {
    if (!selectedCompany) { toast.error("Please select a company"); return; }
    setCreating(true);
    try {
      const payload: Record<string, unknown> = {
        company_id: selectedCompany.id,
        title: dealTitle.trim() || null,
        commodity: dealCommodity.trim() || null,
        quantity_mt: dealQuantity ? parseFloat(dealQuantity) : null,
        target_price: dealTargetPrice ? parseFloat(dealTargetPrice) : null,
        incoterms: dealIncoterms || null,
        payment_terms: dealPaymentTerms || null,
        notes: dealNotes.trim() || null,
        source: "manual",
      };
      if (selectedContact) payload.contact_id = selectedContact.id;

      const { data } = await api.post<Opportunity>("/pipeline", payload);
      toast.success("Opportunity created");
      resetWizard();
      setShowCreate(false);
      fetchData();
      router.push(`/opportunities/${data.id}`);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create opportunity")); }
    setCreating(false);
  }

  function resetWizard() {
    setWizardStep(1);
    setCompanySearch(""); setCompanyResults([]); setSelectedCompany(null);
    setContactSearch(""); setContactResults([]); setSelectedContact(null);
    setShowNewContact(false); setNewContactName(""); setNewContactEmail(""); setNewContactPhone("");
    setDealTitle(""); setProductSearch(""); setProductResults([]); setSelectedProduct(null);
    setDealCommodity(""); setDealQuantity(""); setDealTargetPrice("");
    setDealIncoterms(""); setDealPaymentTerms(""); setDealNotes("");
  }

  // Auto-load contacts for selected company when entering step 2
  useEffect(() => {
    if (wizardStep === 2 && selectedCompany) {
      searchContacts("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wizardStep]);

  // ── Chip select helper ────────────────────────────────────────────
  function ChipSelect({ options, value, onChange, label }: { options: string[]; value: string; onChange: (v: string) => void; label?: string }) {
    return (
      <div>
        {label && <p className="text-[13px] font-medium text-text-primary mb-1.5">{label}</p>}
        <div className="flex flex-wrap gap-1.5">
          {options.map((t) => (
            <button key={t} onClick={() => onChange(value === t ? "" : t)}
              className={`px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border transition-colors cursor-pointer ${
                value === t ? "bg-primary text-text-inverse border-primary" : "bg-surface text-text-secondary border-border"
              }`}>{t}</button>
          ))}
        </div>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <AppShell title="Opportunities">
        <FullWidthLayout>
          <div className="space-y-4">{[1, 2, 3].map((i) => <Skeleton key={i} variant="card" />)}</div>
        </FullWidthLayout>
      </AppShell>
    );
  }

  // ── Empty ─────────────────────────────────────────────────────────
  if (opportunities.length === 0 && !showCreate) {
    return (
      <AppShell title="Opportunities">
        <FullWidthLayout>
          <EmptyState
            icon={<Kanban className="h-12 w-12" />}
            heading="No opportunities yet"
            description="Create your first opportunity to start tracking deals, or move leads from the Leads page."
            actionLabel="Add Opportunity"
            onAction={() => setShowCreate(true)}
          />
          {renderCreateModal()}
        </FullWidthLayout>
      </AppShell>
    );
  }

  // Group by stage
  const byStage: Record<string, Opportunity[]> = {};
  for (const stage of stages) byStage[stage.name] = [];
  for (const opp of opportunities) {
    const sn = opp.stage_name || "Unknown";
    if (!byStage[sn]) byStage[sn] = [];
    byStage[sn].push(opp);
  }

  function renderCreateModal() {
    return (
      <Modal open={showCreate} onOpenChange={(open) => { if (!open) { resetWizard(); setShowCreate(false); } else setShowCreate(true); }}
        title={wizardStep === 1 ? "Step 1: Select Company" : wizardStep === 2 ? "Step 2: Select Contact" : "Step 3: Deal Details"}
        size="md"
        footer={
          <div className="flex justify-between w-full">
            <div>
              {wizardStep > 1 && (
                <Button variant="secondary" onClick={() => setWizardStep(wizardStep - 1)}>
                  <ArrowLeft className="h-4 w-4 mr-1" /> Back
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => { resetWizard(); setShowCreate(false); }}>Cancel</Button>
              {wizardStep === 1 && (
                <Button onClick={() => setWizardStep(2)} disabled={!selectedCompany}>
                  Next <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              )}
              {wizardStep === 2 && (
                <Button onClick={() => setWizardStep(3)}>
                  {selectedContact ? "Next" : "Skip"} <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              )}
              {wizardStep === 3 && (
                <Button onClick={handleCreate} isLoading={creating}>Create Opportunity</Button>
              )}
            </div>
          </div>
        }
      >
        {/* Step 1: Company */}
        {wizardStep === 1 && (
          <div className="space-y-3">
            {selectedCompany ? (
              <div className="flex items-center gap-2 p-3 rounded-[var(--radius-md)] bg-success/5 border border-success/20">
                <Check className="h-4 w-4 text-success" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-text-primary">{selectedCompany.name}</p>
                  <p className="text-xs text-text-secondary">{[selectedCompany.country, selectedCompany.company_type].filter(Boolean).join(" · ")}</p>
                </div>
                <button onClick={() => setSelectedCompany(null)} className="text-text-tertiary hover:text-text-primary cursor-pointer">
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <>
                <div className="relative">
                  <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
                  <input
                    type="text" placeholder="Search companies..."
                    value={companySearch} onChange={(e) => searchCompanies(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-border rounded-[var(--radius-sm)] text-sm bg-surface text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    autoFocus
                  />
                </div>
                {companyResults.length > 0 && (
                  <div className="border border-border rounded-[var(--radius-md)] divide-y divide-border max-h-[200px] overflow-y-auto">
                    {companyResults.map((c) => (
                      <button key={c.id} onClick={() => { setSelectedCompany(c); setCompanySearch(""); setCompanyResults([]); }}
                        className="w-full text-left px-3 py-2 hover:bg-border-light transition-colors cursor-pointer">
                        <p className="text-sm font-medium text-text-primary">{c.name}</p>
                        <p className="text-xs text-text-secondary">{[c.country, c.company_type].filter(Boolean).join(" · ")}</p>
                      </button>
                    ))}
                  </div>
                )}
                {companySearch.trim() && companyResults.length === 0 && (
                  <div className="text-center py-4 space-y-2">
                    <p className="text-sm text-text-secondary">No companies found matching &quot;{companySearch}&quot;</p>
                    <p className="text-xs text-text-tertiary">This company doesn&apos;t exist in your database. Create it now?</p>
                    <Button size="sm" onClick={autoCreateCompany} isLoading={creatingCompany}>
                      <Plus className="h-3.5 w-3.5 mr-1" /> Create &quot;{companySearch.trim()}&quot;
                    </Button>
                  </div>
                )}
                {!companySearch.trim() && (
                  <p className="text-xs text-text-tertiary text-center py-2">Type to search your companies</p>
                )}
              </>
            )}
          </div>
        )}

        {/* Step 2: Contact */}
        {wizardStep === 2 && (
          <div className="space-y-3">
            <p className="text-xs text-text-tertiary">
              Select a contact at <span className="font-medium text-text-secondary">{selectedCompany?.name}</span> (optional)
            </p>

            {selectedContact ? (
              <div className="flex items-center gap-2 p-3 rounded-[var(--radius-md)] bg-success/5 border border-success/20">
                <Check className="h-4 w-4 text-success" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-text-primary">{selectedContact.name}</p>
                  <p className="text-xs text-text-secondary">{[selectedContact.title, selectedContact.email].filter(Boolean).join(" · ")}</p>
                </div>
                <button onClick={() => setSelectedContact(null)} className="text-text-tertiary hover:text-text-primary cursor-pointer">
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : showNewContact ? (
              <div className="space-y-3 p-3 border border-border rounded-[var(--radius-md)]">
                <p className="text-sm font-medium text-text-primary">New Contact</p>
                <Input label="Name" value={newContactName} onChange={(e) => setNewContactName(e.target.value)} autoFocus />
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Email" value={newContactEmail} onChange={(e) => setNewContactEmail(e.target.value)} />
                  <Input label="Phone" value={newContactPhone} onChange={(e) => setNewContactPhone(e.target.value)} />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={createNewContact} isLoading={creatingContact}>Create Contact</Button>
                  <Button size="sm" variant="secondary" onClick={() => setShowNewContact(false)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <>
                <div className="relative">
                  <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
                  <input
                    type="text" placeholder="Search contacts..."
                    value={contactSearch} onChange={(e) => searchContacts(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-border rounded-[var(--radius-sm)] text-sm bg-surface text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
                {contactResults.length > 0 && (
                  <div className="border border-border rounded-[var(--radius-md)] divide-y divide-border max-h-[200px] overflow-y-auto">
                    {contactResults.map((c) => (
                      <button key={c.id} onClick={() => { setSelectedContact(c); setContactSearch(""); setContactResults([]); }}
                        className="w-full text-left px-3 py-2 hover:bg-border-light transition-colors cursor-pointer">
                        <p className="text-sm font-medium text-text-primary">{c.name}</p>
                        <p className="text-xs text-text-secondary">{[c.title, c.email].filter(Boolean).join(" · ")}</p>
                      </button>
                    ))}
                  </div>
                )}
                <button onClick={() => setShowNewContact(true)}
                  className="w-full text-left px-3 py-2 border border-dashed border-border rounded-[var(--radius-md)] hover:bg-border-light transition-colors cursor-pointer">
                  <div className="flex items-center gap-2">
                    <Plus className="h-4 w-4 text-primary" />
                    <span className="text-sm text-primary font-medium">Create new contact</span>
                  </div>
                </button>
              </>
            )}
          </div>
        )}

        {/* Step 3: Deal Details */}
        {wizardStep === 3 && (
          <div className="space-y-4">
            <Input label="Deal Title" placeholder="e.g. Pepper Q2 - Acme Trading" value={dealTitle} onChange={(e) => setDealTitle(e.target.value)} autoFocus />

            <ProductPicker label="Product / Commodity" value={dealCommodity ? [dealCommodity] : []}
              onChange={(v) => setDealCommodity(v[0] || "")} multi={false} placeholder="Select from your catalog..." />

            <Input label="Quantity (MT)" type="number" placeholder="e.g. 50" value={dealQuantity} onChange={(e) => setDealQuantity(e.target.value)} />
            <Input label="Target Price ($/MT)" type="number" placeholder="e.g. 5200" value={dealTargetPrice} onChange={(e) => setDealTargetPrice(e.target.value)} />
            <ChipSelect label="Incoterms" options={INCOTERMS} value={dealIncoterms} onChange={setDealIncoterms} />
            <ChipSelect label="Payment Terms" options={PAYMENT_TERMS} value={dealPaymentTerms} onChange={setDealPaymentTerms} />
            <Textarea label="Notes (optional)" placeholder="Any additional context..." value={dealNotes} onChange={(e) => setDealNotes(e.target.value)} rows={2} />
          </div>
        )}
      </Modal>
    );
  }

  return (
    <AppShell title="Opportunities">
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-text-primary">{opportunities.length} opportunities</h2>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1" /> Add Opportunity
        </Button>
      </div>

      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
        <div className="h-full overflow-x-auto px-4 py-2">
          <div className="flex gap-4 min-w-max">
            {stages.map((stage) => {
              const stageOpps = byStage[stage.name] || [];
              const stageValue = stageOpps.reduce((sum, o) => sum + (o.estimated_value_usd || o.value || 0), 0);
              return (
                <StageColumn key={stage.id} stage={stage} isOver={overStageId === stage.id}>
                  {/* Column header */}
                  <div className="flex items-center justify-between mb-3 px-1">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: stage.color }} />
                      <span className="text-sm font-semibold text-text-primary">{stage.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {stageValue > 0 && <span className="text-[10px] text-text-tertiary">${formatNumber(stageValue)}</span>}
                      <Badge size="sm" variant="outline">{stageOpps.length}</Badge>
                    </div>
                  </div>
                  {/* Cards */}
                  <div className="space-y-2">
                    {stageOpps.map((opp) => (
                      <DraggableCard key={opp.id} opp={opp} onClick={() => router.push(`/opportunities/${opp.id}`)} />
                    ))}
                    {stageOpps.length === 0 && (
                      <div className="rounded-[var(--radius-md)] border border-dashed border-border p-4 text-center">
                        <p className="text-xs text-text-tertiary">No opportunities</p>
                      </div>
                    )}
                  </div>
                </StageColumn>
              );
            })}
          </div>
        </div>

        <DragOverlay>
          {activeOpp && (
            <div className="w-[300px] rounded-[var(--radius-md)] border border-primary/30 bg-surface p-3 shadow-lg rotate-2">
              <CardContent opp={activeOpp} />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {renderCreateModal()}
    </AppShell>
  );
}
