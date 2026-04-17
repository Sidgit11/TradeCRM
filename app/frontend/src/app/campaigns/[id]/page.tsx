"use client";
import type { Campaign, CampaignAnalytics as Analytics } from "@/types";

import { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Play, Pause, XCircle, WhatsappLogo, EnvelopeSimple, ArrowsClockwise,
  PaperPlaneTilt, CheckCircle, XCircle as XIcon, Clock,
  Eye, ArrowLeft, Checks,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime } from "@/lib/utils";



interface MessageItem {
  id: string; contact_name?: string; contact_email?: string;
  channel: string; direction: string; body: string; status: string;
  sent_at: string | null; delivered_at: string | null; opened_at: string | null;
  failed_reason: string | null; created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  sent: "text-info", delivered: "text-success", opened: "text-success",
  read: "text-success", failed: "text-error", bounced: "text-error",
  queued: "text-text-tertiary", sending: "text-warning",
};

export default function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [campRes, analyticsRes] = await Promise.all([
        api.get<Campaign>(`/campaigns/${id}`),
        api.get<Analytics>(`/campaigns/${id}/analytics`),
      ]);
      setCampaign(campRes.data);
      setAnalytics(analyticsRes.data);
    } catch { toast.error("Failed to load campaign data"); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAction = async (action: string) => {
    try {
      const { data } = await api.post<{ status: string; execution?: { sent: number; failed: number; skipped: number } }>(
        `/campaigns/${id}/${action}`
      );
      if (data.execution) {
        toast.success(`Sent: ${data.execution.sent}, Failed: ${data.execution.failed}, Skipped: ${data.execution.skipped}`);
      } else {
        toast.success(`Campaign ${action}d`);
      }
      fetchData();
    } catch (err) { toast.error(getErrorMessage(err, `Failed to ${action} campaign`)); }
  };

  if (loading) {
    return (
      <AppShell title="Campaign"><FullWidthLayout>
        <Skeleton variant="card" className="h-32 mb-4" />
        <Skeleton variant="card" className="h-48" />
      </FullWidthLayout></AppShell>
    );
  }

  if (!campaign) {
    return (
      <AppShell title="Campaign"><FullWidthLayout>
        <p className="text-sm text-text-secondary">Campaign not found</p>
      </FullWidthLayout></AppShell>
    );
  }

  const statusBadge: Record<string, { variant: "success" | "warning" | "error" | "info" | "default"; label: string }> = {
    draft: { variant: "default", label: "Draft" },
    active: { variant: "success", label: "Active" },
    paused: { variant: "warning", label: "Paused" },
    completed: { variant: "info", label: "Completed" },
    cancelled: { variant: "error", label: "Cancelled" },
  };

  const sb = statusBadge[campaign.status] || statusBadge.draft;

  return (
    <AppShell title={campaign.name}>
      <FullWidthLayout>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/campaigns")} className="text-text-tertiary hover:text-text-primary cursor-pointer">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{campaign.name}</h2>
                <Badge variant={sb.variant} size="md">{sb.label}</Badge>
              </div>
              <p className="text-xs text-text-tertiary mt-0.5">
                Created {formatRelativeTime(campaign.created_at)}
                {campaign.started_at && ` / Started ${formatRelativeTime(campaign.started_at)}`}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={fetchData}>
              <ArrowsClockwise className="h-4 w-4 mr-1" /> Refresh
            </Button>
            {campaign.status === "draft" && (
              <Button onClick={() => handleAction("activate")}>
                <Play className="h-4 w-4 mr-1" weight="fill" /> Launch Campaign
              </Button>
            )}
            {campaign.status === "active" && (
              <Button variant="secondary" onClick={() => handleAction("pause")}>
                <Pause className="h-4 w-4 mr-1" weight="fill" /> Pause
              </Button>
            )}
            {campaign.status === "paused" && (
              <Button onClick={() => handleAction("activate")}>
                <Play className="h-4 w-4 mr-1" weight="fill" /> Resume
              </Button>
            )}
            {["draft", "active", "paused"].includes(campaign.status) && (
              <Button variant="ghost" onClick={() => handleAction("cancel")}>
                <XCircle className="h-4 w-4 mr-1" /> Cancel
              </Button>
            )}
          </div>
        </div>

        {/* Metrics */}
        {analytics && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <Card className="p-3 text-center">
              <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">{analytics.total_sent}</p>
              <p className="text-xs text-text-tertiary">Sent</p>
            </Card>
            <Card className="p-3 text-center">
              <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-success">{analytics.delivered}</p>
              <p className="text-xs text-text-tertiary">Delivered ({analytics.delivery_rate}%)</p>
            </Card>
            <Card className="p-3 text-center">
              <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-info">{analytics.opened}</p>
              <p className="text-xs text-text-tertiary">Opened ({analytics.open_rate}%)</p>
            </Card>
            <Card className="p-3 text-center">
              <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-primary">{analytics.replied}</p>
              <p className="text-xs text-text-tertiary">Replied ({analytics.reply_rate}%)</p>
            </Card>
            <Card className="p-3 text-center">
              <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-error">{analytics.failed}</p>
              <p className="text-xs text-text-tertiary">Failed</p>
            </Card>
          </div>
        )}

        {/* Sequence */}
        <Card className="mb-6">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Sequence ({campaign.steps.length} steps)</h3>
          <div className="space-y-2">
            {campaign.steps.sort((a, b) => a.step_number - b.step_number).map((step, i) => (
              <div key={step.id} className="flex items-start gap-3">
                <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold text-text-inverse shrink-0 ${
                  step.channel === "whatsapp" ? "bg-whatsapp" : "bg-email"
                }`}>{step.step_number}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-text-primary">
                      {step.channel === "whatsapp" ? "WhatsApp" : "Email"}
                    </span>
                    {i > 0 && <span className="text-[10px] text-text-tertiary">after {step.delay_days}d</span>}
                    {step.condition !== "always" && <Badge size="sm" variant="outline">{step.condition}</Badge>}
                  </div>
                  <p className="text-xs text-text-secondary mt-0.5 truncate">{step.template_content?.slice(0, 80) || "(empty)"}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Execution log hint */}
        {campaign.status === "draft" && (
          <Card className="border-dashed text-center py-8">
            <PaperPlaneTilt className="h-8 w-8 text-text-tertiary mx-auto mb-2" />
            <p className="text-sm text-text-secondary mb-1">Campaign not launched yet</p>
            <p className="text-xs text-text-tertiary">Click "Launch Campaign" to send messages to all recipients</p>
          </Card>
        )}

        {campaign.status !== "draft" && analytics && analytics.total_sent === 0 && (
          <Card className="border-dashed text-center py-8">
            <Clock className="h-8 w-8 text-text-tertiary mx-auto mb-2" />
            <p className="text-sm text-text-secondary">No messages sent yet</p>
          </Card>
        )}
      </FullWidthLayout>
    </AppShell>
  );
}
