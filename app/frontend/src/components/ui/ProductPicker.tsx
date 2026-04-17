"use client";
import type { Product } from "@/types";
import { useState, useEffect, useRef, useCallback } from "react";
import { Package, X, MagnifyingGlass, Plus } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { Badge } from "./Badge";

interface ProductPickerProps {
  /** Currently selected product names (for multi-select) or single name */
  value: string[];
  /** Called when selection changes */
  onChange: (products: string[]) => void;
  /** Allow selecting multiple products (default true) */
  multi?: boolean;
  /** Label shown above the picker */
  label?: string;
  /** Placeholder text */
  placeholder?: string;
}

/**
 * Product picker that only allows selecting from user's catalog.
 * Fetches products from GET /catalog/products and shows a searchable dropdown.
 */
export function ProductPicker({ value, onChange, multi = true, label, placeholder }: ProductPickerProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchProducts = useCallback(async () => {
    if (loaded) return;
    try {
      const { data } = await api.get<Product[]>("/catalog/products");
      setProducts(data);
      setLoaded(true);
    } catch { /* silent */ }
  }, [loaded]);

  // Fetch on first open
  useEffect(() => {
    if (open) fetchProducts();
  }, [open, fetchProducts]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const filtered = search.trim()
    ? products.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    : products;

  const toggle = (name: string) => {
    if (multi) {
      if (value.includes(name)) onChange(value.filter((v) => v !== name));
      else onChange([...value, name]);
    } else {
      onChange([name]);
      setOpen(false);
      setSearch("");
    }
  };

  const remove = (name: string) => onChange(value.filter((v) => v !== name));

  return (
    <div ref={containerRef} className="relative">
      {label && <p className="text-[13px] font-medium text-text-primary mb-1.5">{label}</p>}

      {/* Selected chips */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {value.map((v) => (
            <span key={v} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
              {v}
              <button onClick={() => remove(v)} className="hover:text-error cursor-pointer"><X className="h-3 w-3" /></button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
        <input
          type="text"
          placeholder={placeholder || "Search your products..."}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onFocus={() => setOpen(true)}
          className="w-full pl-9 pr-3 py-2 border border-border rounded-[var(--radius-sm)] text-sm bg-surface text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-surface border border-border rounded-[var(--radius-md)] shadow-[var(--shadow-lg)] max-h-[200px] overflow-y-auto">
          {filtered.length > 0 ? (
            filtered.map((p) => {
              const selected = value.includes(p.name);
              return (
                <button
                  key={p.id}
                  onClick={() => toggle(p.name)}
                  className={`w-full text-left px-3 py-2 hover:bg-border-light transition-colors cursor-pointer border-b border-border last:border-0 ${selected ? "bg-primary/5" : ""}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-primary">{p.name}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-text-tertiary">{p.origin_country}</span>
                      {selected && <Badge size="sm" variant="success">Selected</Badge>}
                    </div>
                  </div>
                  {p.hs_code && <p className="text-xs text-text-tertiary mt-0.5">HS: {p.hs_code}</p>}
                </button>
              );
            })
          ) : loaded ? (
            <div className="px-3 py-4 text-center">
              <p className="text-sm text-text-secondary mb-1">
                {search.trim() ? `No products matching "${search}"` : "No products in your catalog"}
              </p>
              <a href="/catalog" className="text-xs text-primary hover:underline inline-flex items-center gap-1">
                <Plus className="h-3 w-3" /> Add products in Catalog first
              </a>
            </div>
          ) : (
            <div className="px-3 py-3 text-center">
              <p className="text-xs text-text-tertiary">Loading catalog...</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
