"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  Plus, Package, DownloadSimple, UploadSimple, Trash,
  CaretRight, Check, X, PencilSimple, Warning,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";

// --- Types ---
interface CommodityRef {
  name: string; hs_codes: string[]; aliases: string[];
  category: string | null;
  default_capacity_20ft_mt: string | null; default_capacity_40ft_mt: string | null;
}
interface Grade {
  id: string; name: string; specifications: Record<string, string> | null;
  packaging_type: string | null; packaging_weight_kg: number | null; moq_mt: number | null;
  is_active: boolean;
}
interface Variety { id: string; name: string; is_active: boolean; grades: Grade[]; }
interface Product {
  id: string; tenant_id: string; name: string; origin_country: string;
  hs_code: string | null; description: string | null;
  capacity_20ft_mt: number | null; capacity_40ft_mt: number | null; capacity_40ft_hc_mt: number | null;
  shelf_life_days: number | null; certifications: string[] | null; aliases: string[] | null;
  is_active: boolean; varieties: Variety[]; created_at: string;
}

interface CsvRow {
  product_name: string; origin_country: string; variety: string;
  grade: string; hs_code: string; description: string;
  isValid: boolean; error: string;
}

// --- CSV Parser ---
function parseCsvText(text: string): CsvRow[] {
  const lines = text.split("\n").filter((l) => l.trim());
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase().replace(/\s+/g, "_"));
  const rows: CsvRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(",").map((v) => v.trim());
    const row: Record<string, string> = {};
    headers.forEach((h, idx) => { row[h] = values[idx] || ""; });
    const pname = row["product_name"] || "";
    const origin = row["origin_country"] || "";
    let isValid = true;
    let error = "";
    if (!pname) { isValid = false; error = "Product name required"; }
    else if (!origin) { isValid = false; error = "Origin country required"; }
    rows.push({
      product_name: pname, origin_country: origin,
      variety: row["variety"] || "", grade: row["grade"] || "",
      hs_code: row["hs_code"] || "", description: row["description"] || "",
      isValid, error,
    });
  }
  return rows;
}

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Add product form
  const [pName, setPName] = useState("");
  const [pOrigin, setPOrigin] = useState("");
  const [pHs, setPHs] = useState("");
  const [pDesc, setPDesc] = useState("");
  const [pCap20, setPCap20] = useState("");
  const [pCap40, setPCap40] = useState("");
  const [pCap40hc, setPCap40hc] = useState("");
  const [pAliases, setPAliases] = useState("");
  const [pCerts, setPCerts] = useState("");
  const [pShelfLife, setPShelfLife] = useState("");

  // Commodity autocomplete
  const [commodityResults, setCommodityResults] = useState<CommodityRef[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCommoditySearch = (value: string) => {
    setPName(value);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (value.length < 2) { setCommodityResults([]); setShowSuggestions(false); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`http://localhost:8000/catalog/commodities/search?q=${encodeURIComponent(value)}`);
        const data: CommodityRef[] = await res.json();
        setCommodityResults(data);
        setShowSuggestions(data.length > 0);
      } catch { setCommodityResults([]); }
    }, 200);
  };

  const handleSelectCommodity = (c: CommodityRef) => {
    setPName(c.name);
    setPHs(c.hs_codes.join(", "));
    setPAliases(c.aliases.slice(0, 3).join(", "));
    if (c.default_capacity_20ft_mt) setPCap20(c.default_capacity_20ft_mt);
    if (c.default_capacity_40ft_mt) setPCap40(c.default_capacity_40ft_mt);
    setShowSuggestions(false);
    setCommodityResults([]);
  };

  // Add variety/grade inline
  const [addingVariety, setAddingVariety] = useState<string | null>(null);
  const [newVarietyName, setNewVarietyName] = useState("");
  const [addingGrade, setAddingGrade] = useState<string | null>(null);
  const [newGradeName, setNewGradeName] = useState("");

  // CSV import flow
  const [showImport, setShowImport] = useState(false);
  const [csvRows, setCsvRows] = useState<CsvRow[]>([]);
  const [importStep, setImportStep] = useState<"upload" | "preview" | "done">("upload");
  const [importing, setImporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Edit product
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editName, setEditName] = useState("");
  const [editOrigin, setEditOrigin] = useState("");
  const [editHs, setEditHs] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editCap20, setEditCap20] = useState("");
  const [editCap40, setEditCap40] = useState("");
  const [editAliases, setEditAliases] = useState("");
  const [editCerts, setEditCerts] = useState("");

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [saving, setSaving] = useState(false);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Product[]>("/catalog/products");
      setProducts(data);
    } catch { toast.error("Failed to load products"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  // --- Product CRUD ---
  const handleCreateProduct = async () => {
    if (!pName.trim() || !pOrigin.trim()) { toast.error("Product name and origin are required"); return; }
    setSaving(true);
    try {
      await api.post("/catalog/products", {
        name: pName.trim(), origin_country: pOrigin.trim(),
        hs_code: pHs.trim() || undefined, description: pDesc.trim() || undefined,
        shelf_life_days: pShelfLife ? parseInt(pShelfLife) : undefined,
        capacity_20ft_mt: pCap20 ? parseFloat(pCap20) : undefined,
        capacity_40ft_mt: pCap40 ? parseFloat(pCap40) : undefined,
        capacity_40ft_hc_mt: pCap40hc ? parseFloat(pCap40hc) : undefined,
        aliases: pAliases ? pAliases.split(",").map((s: string) => s.trim()).filter(Boolean) : undefined,
        certifications: pCerts ? pCerts.split(",").map((s: string) => s.trim()).filter(Boolean) : undefined,
      });
      toast.success("Product created");
      setShowAdd(false);
      setPName(""); setPOrigin(""); setPHs(""); setPDesc(""); setPCap20(""); setPCap40(""); setPCap40hc(""); setPAliases(""); setPCerts(""); setPShelfLife("");
      fetchProducts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to create product")); }
    setSaving(false);
  };

  const handleAddVariety = async (productId: string) => {
    if (!newVarietyName.trim()) return;
    try {
      await api.post(`/catalog/products/${productId}/varieties?name=${encodeURIComponent(newVarietyName.trim())}`);
      toast.success("Variety added");
      setAddingVariety(null); setNewVarietyName("");
      fetchProducts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to add variety")); }
  };

  const handleAddGrade = async (varietyId: string) => {
    if (!newGradeName.trim()) return;
    try {
      await api.post(`/catalog/varieties/${varietyId}/grades?name=${encodeURIComponent(newGradeName.trim())}`);
      toast.success("Grade added");
      setAddingGrade(null); setNewGradeName("");
      fetchProducts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to add grade")); }
  };

  // --- CSV Import ---
  const openEditProduct = (product: Product) => {
    setEditingProduct(product);
    setEditName(product.name);
    setEditOrigin(product.origin_country);
    setEditHs(product.hs_code || "");
    setEditDesc(product.description || "");
    setEditCap20(product.capacity_20ft_mt?.toString() || "");
    setEditCap40(product.capacity_40ft_mt?.toString() || "");
    setEditAliases(product.aliases?.join(", ") || "");
    setEditCerts(product.certifications?.join(", ") || "");
  };

  const handleUpdateProduct = async () => {
    if (!editingProduct || !editName.trim()) return;
    setSaving(true);
    try {
      await api.put(`/catalog/products/${editingProduct.id}`, {
        name: editName.trim(),
        origin_country: editOrigin.trim() || undefined,
        hs_code: editHs.trim() || undefined,
        description: editDesc.trim() || undefined,
        capacity_20ft_mt: editCap20 ? parseFloat(editCap20) : undefined,
        capacity_40ft_mt: editCap40 ? parseFloat(editCap40) : undefined,
        aliases: editAliases ? editAliases.split(",").map((s: string) => s.trim()).filter(Boolean) : undefined,
        certifications: editCerts ? editCerts.split(",").map((s: string) => s.trim()).filter(Boolean) : undefined,
      });
      toast.success("Product updated");
      setEditingProduct(null);
      fetchProducts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to update product")); }
    setSaving(false);
  };

  const handleDeleteProduct = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/catalog/products/${deleteTarget.id}`);
      toast.success(`${deleteTarget.name} removed from catalog`);
      setDeleteTarget(null);
      fetchProducts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to delete product")); }
    setDeleting(false);
  };

  const handleDownloadTemplate = () => {
    window.open("http://localhost:8000/catalog/products/template/download", "_blank");
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const rows = parseCsvText(text);
      if (rows.length === 0) { toast.error("No data rows found in CSV"); return; }
      setCsvRows(rows);
      setImportStep("preview");
    };
    reader.readAsText(file);
  };

  const handleCsvRowEdit = (index: number, field: string, value: string) => {
    setCsvRows((prev) => {
      const updated = [...prev];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (updated[index] as any)[field] = value;
      // Re-validate
      updated[index].isValid = !!updated[index].product_name && !!updated[index].origin_country;
      updated[index].error = !updated[index].product_name ? "Product name required" : !updated[index].origin_country ? "Origin required" : "";
      return updated;
    });
  };

  const handleCsvRowDelete = (index: number) => {
    setCsvRows((prev) => prev.filter((_, i) => i !== index));
  };

  const handleImportConfirm = async () => {
    const validRows = csvRows.filter((r) => r.isValid);
    if (validRows.length === 0) { toast.error("No valid rows to import"); return; }

    setImporting(true);
    try {
      // Build CSV string from the (possibly edited) rows
      const csvContent = [
        "product_name,origin_country,variety,grade,hs_code,description",
        ...validRows.map((r) => `${r.product_name},${r.origin_country},${r.variety},${r.grade},${r.hs_code},${r.description}`),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv" });
      const formData = new FormData();
      formData.append("file", blob, "import.csv");

      const response = await fetch("http://localhost:8000/catalog/products/import", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();

      toast.success(`Imported: ${result.products_created} products, ${result.varieties_created} varieties, ${result.grades_created} grades`);
      setImportStep("done");
      fetchProducts();
    } catch (err) { toast.error(getErrorMessage(err, "Import failed")); }
    setImporting(false);
  };

  const resetImport = () => {
    setShowImport(false);
    setCsvRows([]);
    setImportStep("upload");
    if (fileRef.current) fileRef.current.value = "";
  };

  const validCount = csvRows.filter((r) => r.isValid).length;
  const invalidCount = csvRows.filter((r) => !r.isValid).length;

  return (
    <AppShell title="Product Catalog">
      <FullWidthLayout>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Your Products</h2>
            <p className="text-sm text-text-secondary mt-0.5">Manage your commodity catalog, varieties, and grades</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { resetImport(); setShowImport(true); }}>
              <UploadSimple className="h-4 w-4 mr-1" /> Import CSV
            </Button>
            <Button onClick={() => setShowAdd(true)}>
              <Plus className="h-4 w-4 mr-1" /> Add Product
            </Button>
          </div>
        </div>

        {/* Product List */}
        {products.length === 0 && !loading ? (
          <EmptyState
            icon={<Package className="h-12 w-12" />}
            heading="No products in catalog"
            description="Add your commodities with varieties and grades to enable pricing and lead matching."
            actionLabel="Add First Product"
            onAction={() => setShowAdd(true)}
          />
        ) : (
          <div className="space-y-3">
            {products.map((product) => (
              <Card key={product.id} className="p-0 overflow-hidden">
                <div
                  onClick={() => setExpanded(expanded === product.id ? null : product.id)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-border-light/50 transition-colors cursor-pointer"
                  role="button" tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter") setExpanded(expanded === product.id ? null : product.id); }}
                >
                  <div className="flex items-center gap-3">
                    <Package className="h-5 w-5 text-primary shrink-0" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-text-primary">{product.name}</span>
                        <Badge size="sm">{product.origin_country}</Badge>
                        {product.hs_code && <Badge size="sm" variant="outline">HS: {product.hs_code}</Badge>}
                      </div>
                      <p className="text-xs text-text-tertiary mt-0.5">
                        {product.varieties.length} {product.varieties.length === 1 ? "variety" : "varieties"}
                        {" / "}
                        {product.varieties.reduce((sum, v) => sum + v.grades.length, 0)} grades
                        {product.capacity_20ft_mt && ` / ${product.capacity_20ft_mt}MT per 20ft`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); openEditProduct(product); }}
                      className="p-1.5 rounded text-text-tertiary hover:text-primary hover:bg-primary/10 transition-colors cursor-pointer"
                      title="Edit product"
                    >
                      <PencilSimple className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(product); }}
                      className="p-1.5 rounded text-text-tertiary hover:text-error hover:bg-error/10 transition-colors cursor-pointer"
                      title="Delete product"
                    >
                      <Trash className="h-4 w-4" />
                    </button>
                    <CaretRight className={`h-4 w-4 text-text-tertiary transition-transform ${expanded === product.id ? "rotate-90" : ""}`} />
                  </div>
                </div>

                {expanded === product.id && (
                  <div className="border-t border-border px-4 py-3 bg-border-light/30">
                    {product.aliases && product.aliases.length > 0 && (
                      <p className="text-xs text-text-tertiary mb-2">Aliases: {product.aliases.join(", ")}</p>
                    )}
                    {product.certifications && product.certifications.length > 0 && (
                      <div className="flex gap-1 mb-3">
                        {product.certifications.map((c) => <Badge key={c} size="sm" variant="success">{c}</Badge>)}
                      </div>
                    )}

                    {product.varieties.length === 0 && (
                      <p className="text-xs text-text-tertiary mb-2">No varieties yet. Add one below.</p>
                    )}

                    {product.varieties.map((variety) => (
                      <div key={variety.id} className="mb-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-text-primary">{variety.name}</span>
                          <button onClick={() => { setAddingGrade(variety.id); setNewGradeName(""); }} className="text-xs text-primary hover:underline cursor-pointer">+ Add Grade</button>
                        </div>
                        <div className="flex flex-wrap gap-2 ml-3">
                          {variety.grades.map((grade) => (
                            <div key={grade.id} className="text-xs px-2 py-1 rounded-[var(--radius-sm)] bg-surface border border-border">
                              <span className="font-medium">{grade.name}</span>
                              {grade.packaging_type && <span className="text-text-tertiary ml-1">({grade.packaging_type})</span>}
                              {grade.moq_mt && <span className="text-text-tertiary ml-1">MOQ: {grade.moq_mt}MT</span>}
                            </div>
                          ))}
                          {variety.grades.length === 0 && <span className="text-xs text-text-tertiary">No grades yet</span>}
                        </div>
                        {addingGrade === variety.id && (
                          <div className="flex gap-2 mt-2 ml-3">
                            <Input inputSize="sm" placeholder="Grade name (e.g. 500GL)" value={newGradeName} onChange={(e) => setNewGradeName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAddGrade(variety.id)} />
                            <Button size="sm" onClick={() => handleAddGrade(variety.id)}>Add</Button>
                            <Button size="sm" variant="ghost" onClick={() => setAddingGrade(null)}>Cancel</Button>
                          </div>
                        )}
                      </div>
                    ))}

                    {addingVariety === product.id ? (
                      <div className="flex gap-2 mt-2">
                        <Input inputSize="sm" placeholder="Variety name (e.g. Malabar)" value={newVarietyName} onChange={(e) => setNewVarietyName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAddVariety(product.id)} />
                        <Button size="sm" onClick={() => handleAddVariety(product.id)}>Add</Button>
                        <Button size="sm" variant="ghost" onClick={() => setAddingVariety(null)}>Cancel</Button>
                      </div>
                    ) : (
                      <button onClick={() => { setAddingVariety(product.id); setNewVarietyName(""); }} className="text-xs text-primary hover:underline cursor-pointer mt-1">+ Add Variety</button>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* Add Product Modal */}
        <Modal open={showAdd} onOpenChange={setShowAdd} title="Add Product" size="md" footer={<><Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button><Button onClick={handleCreateProduct} isLoading={saving}>Save Product</Button></>}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="relative">
                <Input
                  label="Product Name *"
                  placeholder="Start typing... e.g. Black Pepper"
                  value={pName}
                  onChange={(e) => handleCommoditySearch(e.target.value)}
                  onFocus={() => { if (commodityResults.length > 0) setShowSuggestions(true); }}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                />
                {showSuggestions && (
                  <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-surface border border-border rounded-[var(--radius-md)] shadow-[var(--shadow-lg)] max-h-[200px] overflow-y-auto">
                    {commodityResults.map((c) => (
                      <button
                        key={c.name}
                        onMouseDown={() => handleSelectCommodity(c)}
                        className="w-full text-left px-3 py-2 hover:bg-border-light transition-colors cursor-pointer border-b border-border last:border-0"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-text-primary">{c.name}</span>
                          {c.category && <Badge size="sm">{c.category}</Badge>}
                        </div>
                        <p className="text-xs text-text-tertiary mt-0.5">
                          HS: {c.hs_codes.join(", ")} | {c.aliases.slice(0, 2).join(", ")}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Input label="Origin Country *" placeholder="e.g. India" value={pOrigin} onChange={(e) => setPOrigin(e.target.value)} />
            </div>
            <Input label="HS Code(s)" placeholder="Auto-filled from selection" value={pHs} onChange={(e) => setPHs(e.target.value)} helperText="Auto-fills when you select a commodity above" />
            <p className="text-xs text-text-tertiary">You can add description, certifications, container capacity and more after creation.</p>
          </div>
        </Modal>

        {/* CSV Import Modal */}
        <Modal open={showImport} onOpenChange={(v) => { if (!v) resetImport(); }} title="Import Products from CSV" size="lg">
          {importStep === "upload" && (
            <div className="py-4">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-text-secondary">Upload a CSV file to bulk-add products, varieties, and grades.</p>
                <Button variant="secondary" size="sm" onClick={handleDownloadTemplate}>
                  <DownloadSimple className="h-4 w-4 mr-1" /> Download Template
                </Button>
              </div>
              <div
                className="border-2 border-dashed border-border rounded-[var(--radius-md)] p-8 text-center hover:border-primary-lighter transition-colors cursor-pointer"
                onClick={() => fileRef.current?.click()}
              >
                <UploadSimple className="h-10 w-10 text-text-tertiary mx-auto mb-3" />
                <p className="text-sm text-text-secondary mb-1">Click to select your CSV file</p>
                <p className="text-xs text-text-tertiary">Expected columns: product_name, origin_country, variety, grade, hs_code, description</p>
                <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileSelect} />
              </div>
            </div>
          )}

          {importStep === "preview" && (
            <div className="py-2">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Badge variant="success" size="md">{validCount} valid</Badge>
                  {invalidCount > 0 && <Badge variant="error" size="md">{invalidCount} errors</Badge>}
                  <span className="text-xs text-text-tertiary">{csvRows.length} rows total</span>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => { setImportStep("upload"); setCsvRows([]); }}>Back</Button>
                  <Button size="sm" onClick={handleImportConfirm} isLoading={importing} disabled={validCount === 0}>
                    <Check className="h-4 w-4 mr-1" /> Import {validCount} Rows
                  </Button>
                </div>
              </div>

              <div className="max-h-[400px] overflow-auto border border-border rounded-[var(--radius-md)]">
                <table className="w-full text-xs">
                  <thead className="bg-border-light sticky top-0">
                    <tr>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary">#</th>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary">Product</th>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary">Origin</th>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary">Variety</th>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary">Grade</th>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary">HS Code</th>
                      <th className="text-left px-2 py-2 font-medium text-text-secondary w-8"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvRows.map((row, idx) => (
                      <tr key={idx} className={`border-t border-border ${!row.isValid ? "bg-error/5" : "hover:bg-border-light/50"}`}>
                        <td className="px-2 py-1.5 text-text-tertiary">{idx + 1}</td>
                        <td className="px-2 py-1.5">
                          <input
                            value={row.product_name}
                            onChange={(e) => handleCsvRowEdit(idx, "product_name", e.target.value)}
                            className="w-full bg-transparent border-none text-xs text-text-primary outline-none focus:ring-1 focus:ring-primary/30 rounded px-1"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            value={row.origin_country}
                            onChange={(e) => handleCsvRowEdit(idx, "origin_country", e.target.value)}
                            className="w-full bg-transparent border-none text-xs text-text-primary outline-none focus:ring-1 focus:ring-primary/30 rounded px-1"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            value={row.variety}
                            onChange={(e) => handleCsvRowEdit(idx, "variety", e.target.value)}
                            className="w-full bg-transparent border-none text-xs text-text-primary outline-none focus:ring-1 focus:ring-primary/30 rounded px-1"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            value={row.grade}
                            onChange={(e) => handleCsvRowEdit(idx, "grade", e.target.value)}
                            className="w-full bg-transparent border-none text-xs text-text-primary outline-none focus:ring-1 focus:ring-primary/30 rounded px-1"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <input
                            value={row.hs_code}
                            onChange={(e) => handleCsvRowEdit(idx, "hs_code", e.target.value)}
                            className="w-full bg-transparent border-none text-xs text-text-primary outline-none focus:ring-1 focus:ring-primary/30 rounded px-1"
                          />
                        </td>
                        <td className="px-2 py-1.5">
                          <div className="flex items-center gap-1">
                            {!row.isValid && (
                              <span title={row.error}><Warning className="h-3.5 w-3.5 text-error" weight="fill" /></span>
                            )}
                            <button onClick={() => handleCsvRowDelete(idx)} className="text-text-tertiary hover:text-error cursor-pointer">
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {importStep === "done" && (
            <div className="py-8 text-center">
              <Check className="h-12 w-12 text-success mx-auto mb-3" weight="bold" />
              <p className="text-sm font-medium text-text-primary mb-1">Import complete</p>
              <p className="text-xs text-text-secondary mb-4">Your catalog has been updated.</p>
              <Button onClick={resetImport}>Done</Button>
            </div>
          )}
        </Modal>

        {/* Edit Product Modal */}
        <Modal
          open={!!editingProduct}
          onOpenChange={(v) => { if (!v) setEditingProduct(null); }}
          title={`Edit: ${editingProduct?.name || ""}`}
          size="lg"
          footer={
            <>
              <Button variant="secondary" onClick={() => setEditingProduct(null)}>Cancel</Button>
              <Button onClick={handleUpdateProduct} isLoading={saving}>Save Changes</Button>
            </>
          }
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input label="Product Name" value={editName} onChange={(e) => setEditName(e.target.value)} />
              <Input label="Origin Country" value={editOrigin} onChange={(e) => setEditOrigin(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input label="HS Code(s)" value={editHs} onChange={(e) => setEditHs(e.target.value)} />
              <Input label="Description" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
            </div>
            <div className="border-t border-border pt-4">
              <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">Container Capacity (MT)</p>
              <div className="grid grid-cols-2 gap-4">
                <Input label="20ft" value={editCap20} onChange={(e) => setEditCap20(e.target.value)} />
                <Input label="40ft" value={editCap40} onChange={(e) => setEditCap40(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Aliases (comma-separated)" value={editAliases} onChange={(e) => setEditAliases(e.target.value)} />
              <Input label="Certifications (comma-separated)" value={editCerts} onChange={(e) => setEditCerts(e.target.value)} />
            </div>
          </div>
        </Modal>

        {/* Delete Confirmation Modal */}
        <Modal
          open={!!deleteTarget}
          onOpenChange={(v) => { if (!v) setDeleteTarget(null); }}
          title="Remove Product"
          size="sm"
          footer={
            <>
              <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
              <Button variant="destructive" onClick={handleDeleteProduct} isLoading={deleting}>Yes, Remove</Button>
            </>
          }
        >
          <div className="py-2">
            <div className="flex items-start gap-3 mb-4">
              <div className="shrink-0 h-10 w-10 rounded-full bg-error/10 flex items-center justify-center">
                <Warning className="h-5 w-5 text-error" weight="fill" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary mb-1">
                  Remove "{deleteTarget?.name}" from your catalog?
                </p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  This may impact other workflows that reference this product, including FOB pricing, lead matching, and campaign personalization. The product will be hidden but not permanently deleted.
                </p>
              </div>
            </div>
          </div>
        </Modal>
      </FullWidthLayout>
    </AppShell>
  );
}
