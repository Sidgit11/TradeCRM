"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";

const SUGGESTED_QUERIES = [
  "Pepper importers in USA",
  "Coffee buyers in Germany",
  "Spice importers in UAE",
  "Seafood buyers in Japan",
  "Turmeric importers in Europe",
];

export default function DiscoverPage() {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSearch = async (searchQuery: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setSearching(true);
    setResult(null);
    try {
      const { data } = await api.post<{ agent_task_id: string; status: string; message: string }>(
        "/discover/search",
        { query: q },
      );
      setResult(`Discovery search queued (Task: ${data.agent_task_id.slice(0, 8)}). Results will appear here once the AI agent completes research.`);
    } catch {
      setResult("Search request failed. Please try again.");
    }
    setSearching(false);
  };

  return (
    <AppShell title="Discover Buyers">
      <div className="flex-1 px-6 py-10">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary text-center mb-2">
            What buyers are you looking for?
          </h2>
          <p className="text-sm text-text-secondary text-center mb-6">
            Use natural language to discover verified importers across global markets.
          </p>

          <div className="flex gap-2 mb-4">
            <Input
              type="search"
              placeholder="e.g. Black pepper importers in the United States"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch("")}
              className="flex-1"
            />
            <Button onClick={() => handleSearch("")} isLoading={searching}>
              <MagnifyingGlass className="h-4 w-4 mr-1" /> Search
            </Button>
          </div>

          <div className="flex flex-wrap gap-2 mb-8">
            {SUGGESTED_QUERIES.map((sq) => (
              <button
                key={sq}
                onClick={() => { setQuery(sq); handleSearch(sq); }}
                className="px-3 py-1.5 rounded-[var(--radius-full)] text-xs border border-border text-text-secondary hover:border-primary-lighter hover:text-primary transition-colors cursor-pointer"
              >
                {sq}
              </button>
            ))}
          </div>

          {result && (
            <div className="rounded-[var(--radius-md)] border border-border bg-surface p-6">
              <p className="text-sm text-text-secondary">{result}</p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
