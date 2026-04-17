"use client";
import type { PipelineOpportunity as Opportunity, PipelineStage as Stage } from "@/types";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Kanban, Buildings, User, Package, CurrencyDollar,
  CalendarBlank, Scales, Truck, TestTube, ArrowRight,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime, formatNumber } from "@/lib/utils";



export default function PipelinePage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [oppsRes, stagesRes] = await Promise.all([
        api.get<Opportunity[]>("/pipeline"),
        api.get<Stage[]>("/pipeline/stages"),
      ]);
      setOpportunities(oppsRes.data);
      setStages(stagesRes.data);
    } catch { toast.error("Failed to load pipeline"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <AppShell title="Pipeline">
        <FullWidthLayout>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => <Skeleton key={i} variant="card" />)}
          </div>
        </FullWidthLayout>
      </AppShell>
    );
  }

  if (opportunities.length === 0) {
    return (
      <AppShell title="Pipeline">
        <FullWidthLayout>
          <EmptyState
            icon={<Kanban className="h-12 w-12" />}
            heading="No opportunities yet"
            description="Move leads to the pipeline from the Leads page, or add companies to start tracking deals."
            actionLabel="Go to Leads"
            onAction={() => window.location.href = "/leads"}
          />
        </FullWidthLayout>
      </AppShell>
    );
  }

  // Group opportunities by stage
  const byStage: Record<string, Opportunity[]> = {};
  for (const stage of stages) {
    byStage[stage.name] = [];
  }
  for (const opp of opportunities) {
    const stageName = opp.stage_name || "Unknown";
    if (!byStage[stageName]) byStage[stageName] = [];
    byStage[stageName].push(opp);
  }

  return (
    <AppShell title="Pipeline">
      <div className="h-full overflow-x-auto px-4 py-4">
        <div className="flex gap-4 min-w-max">
          {stages.map((stage) => {
            const stageOpps = byStage[stage.name] || [];
            const stageValue = stageOpps.reduce((sum, o) => sum + (o.estimated_value_usd || o.value || 0), 0);
            return (
              <div key={stage.id} className="w-[300px] shrink-0">
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
                    <div
                      key={opp.id}
                      className="rounded-[var(--radius-md)] border border-border bg-surface p-3 hover:shadow-[var(--shadow-md)] transition-shadow"
                    >
                      {/* Title / Company */}
                      {opp.title && (
                        <p className="text-xs font-semibold text-text-primary mb-1 truncate">{opp.title}</p>
                      )}
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

                      {/* Commodity & Quantity */}
                      {opp.commodity && (
                        <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
                          <Package className="h-3 w-3 shrink-0" />
                          <span>{opp.commodity}</span>
                          {opp.quantity_mt && <span className="text-text-tertiary">({opp.quantity_mt} MT)</span>}
                        </div>
                      )}

                      {/* Pricing row */}
                      {(opp.target_price || opp.our_price) && (
                        <div className="flex items-center gap-2 text-xs mb-1">
                          <CurrencyDollar className="h-3 w-3 text-text-tertiary shrink-0" />
                          {opp.target_price && <span className="text-text-secondary">Target: ${formatNumber(opp.target_price)}</span>}
                          {opp.our_price && <span className="text-success">Ours: ${formatNumber(opp.our_price)}</span>}
                          {opp.competitor_price && <span className="text-error">Comp: ${formatNumber(opp.competitor_price)}</span>}
                        </div>
                      )}

                      {/* Trade terms */}
                      {(opp.incoterms || opp.payment_terms) && (
                        <div className="flex items-center gap-2 text-[10px] text-text-tertiary mb-1">
                          {opp.incoterms && <Badge size="sm" variant="outline">{opp.incoterms}</Badge>}
                          {opp.payment_terms && <Badge size="sm" variant="outline">{opp.payment_terms}</Badge>}
                        </div>
                      )}

                      {/* Containers & shipment */}
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

                      {/* Sample status */}
                      {opp.sample_sent && (
                        <div className="flex items-center gap-1 text-[10px] mb-1">
                          <TestTube className="h-3 w-3 text-text-tertiary" />
                          <span className={opp.sample_approved === true ? "text-success" : opp.sample_approved === false ? "text-error" : "text-warning"}>
                            Sample {opp.sample_approved === true ? "Approved" : opp.sample_approved === false ? "Rejected" : "Sent"}
                          </span>
                        </div>
                      )}

                      {/* Footer */}
                      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-border">
                        <div className="flex items-center gap-2">
                          <Badge size="sm" variant="outline">{opp.source}</Badge>
                          {opp.probability > 0 && (
                            <span className="text-[10px] text-text-tertiary">{opp.probability}%</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {opp.follow_up_date && (
                            <span className="text-[10px] text-warning">Follow-up: {opp.follow_up_date}</span>
                          )}
                          <span className="text-[10px] text-text-tertiary">{formatRelativeTime(opp.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {stageOpps.length === 0 && (
                    <div className="rounded-[var(--radius-md)] border border-dashed border-border p-4 text-center">
                      <p className="text-xs text-text-tertiary">No opportunities</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
