"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  PaperPlaneTilt, Plus, WhatsappLogo, EnvelopeSimple,
  Play, Pause, XCircle, ChartBar,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

interface Campaign {
  id: string;
  name: string;
  type: string;
  status: string;
  contact_list_id: string | null;
  steps: Array<{ channel: string; step_number: number }>;
  created_at: string;
  started_at: string | null;
}

const STATUS_BADGES: Record<string, { variant: "success" | "warning" | "error" | "info" | "default"; label: string }> = {
  draft: { variant: "default", label: "Draft" },
  active: { variant: "success", label: "Active" },
  paused: { variant: "warning", label: "Paused" },
  completed: { variant: "info", label: "Completed" },
  cancelled: { variant: "error", label: "Cancelled" },
};

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Campaign[]>("/campaigns?limit=50");
      setCampaigns(data);
    } catch (err) { toast.error(getErrorMessage(err, "Action failed")); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchCampaigns(); }, [fetchCampaigns]);

  const handleAction = async (id: string, action: string) => {
    try {
      await api.post(`/campaigns/${id}/${action}`);
      fetchCampaigns();
    } catch (err) { toast.error(getErrorMessage(err, "Action failed")); }
  };

  return (
    <AppShell title="Campaigns">
      <FullWidthLayout>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">Campaigns</h2>
            {campaigns.length > 0 && <p className="text-sm text-text-secondary">{campaigns.length} campaigns</p>}
          </div>
          <Button onClick={() => router.push("/campaigns/new")}>
            <Plus className="h-4 w-4 mr-1" /> New Campaign
          </Button>
        </div>

        {loading ? (
          <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} variant="card" className="h-20" />)}</div>
        ) : campaigns.length === 0 ? (
          <EmptyState
            icon={<PaperPlaneTilt className="h-12 w-12" />}
            heading="No campaigns yet"
            description="Create multi-channel outreach campaigns with AI-personalized messages."
            actionLabel="Create Campaign"
            onAction={() => router.push("/campaigns/new")}
          />
        ) : (
          <div className="space-y-2">
            {campaigns.map((c) => {
              const statusInfo = STATUS_BADGES[c.status] || STATUS_BADGES.draft;
              const waSteps = c.steps.filter((s) => s.channel === "whatsapp").length;
              const emailSteps = c.steps.filter((s) => s.channel === "email").length;

              return (
                <div key={c.id}
                  className="flex items-center justify-between p-4 rounded-[var(--radius-md)] border border-border bg-surface hover:shadow-[var(--shadow-sm)] transition-shadow cursor-pointer"
                  onClick={() => router.push(`/campaigns/${c.id}`)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-text-primary">{c.name}</span>
                      <Badge size="sm" variant={statusInfo.variant}>{statusInfo.label}</Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-tertiary">
                      <span>{c.steps.length} step{c.steps.length !== 1 ? "s" : ""}</span>
                      {waSteps > 0 && (
                        <span className="flex items-center gap-0.5">
                          <WhatsappLogo className="h-3 w-3 text-whatsapp" weight="fill" /> {waSteps}
                        </span>
                      )}
                      {emailSteps > 0 && (
                        <span className="flex items-center gap-0.5">
                          <EnvelopeSimple className="h-3 w-3 text-email" weight="fill" /> {emailSteps}
                        </span>
                      )}
                      <span>{formatRelativeTime(c.created_at)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    {c.status === "draft" && (
                      <Button size="sm" variant="ghost" onClick={() => handleAction(c.id, "activate")} title="Activate">
                        <Play className="h-4 w-4 text-success" weight="fill" />
                      </Button>
                    )}
                    {c.status === "active" && (
                      <Button size="sm" variant="ghost" onClick={() => handleAction(c.id, "pause")} title="Pause">
                        <Pause className="h-4 w-4 text-warning" weight="fill" />
                      </Button>
                    )}
                    {c.status === "paused" && (
                      <Button size="sm" variant="ghost" onClick={() => handleAction(c.id, "activate")} title="Resume">
                        <Play className="h-4 w-4 text-success" weight="fill" />
                      </Button>
                    )}
                    {(c.status === "draft" || c.status === "active" || c.status === "paused") && (
                      <Button size="sm" variant="ghost" onClick={() => handleAction(c.id, "cancel")} title="Cancel">
                        <XCircle className="h-4 w-4 text-error" />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </FullWidthLayout>
    </AppShell>
  );
}
