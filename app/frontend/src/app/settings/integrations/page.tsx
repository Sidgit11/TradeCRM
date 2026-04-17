"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { SettingsNav } from "@/components/layout/SettingsNav";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import {
  EnvelopeSimple, GoogleLogo, MicrosoftOutlookLogo,
  WhatsappLogo, Plugs, Check, Trash, ArrowsClockwise,
  ShieldCheck, Warning, Eye, PaperPlaneTilt, Tag,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime } from "@/lib/utils";

interface EmailAccount {
  id: string;
  email_address: string;
  provider: string;
  display_name: string | null;
  is_active: boolean;
  last_sync_at: string | null;
  created_at: string;
}

// --- WhatsApp Section Component ---
function WhatsAppSection() {
  const [waStatus, setWaStatus] = useState<{ status: string; phone: string | null; app_id: string | null; connected_at: string | null } | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [embedUrl, setEmbedUrl] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<{ status: string; phone: string | null; app_id: string | null; connected_at: string | null }>("/whatsapp/status");
        setWaStatus(data);
      } catch { toast.error("Failed to load data"); }
    })();
  }, []);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const { data } = await api.post<{ status: string; phone?: string; embed_url?: string; mode?: string }>(
        "/whatsapp/onboarding/start"
      );
      if (data.status === "active") {
        setWaStatus({ status: "active", phone: data.phone || null, app_id: null, connected_at: new Date().toISOString() });
        toast.success(`WhatsApp connected: ${data.phone || "ready"}`);
      } else if (data.embed_url) {
        setEmbedUrl(data.embed_url);
        window.open(data.embed_url, "_blank", "width=600,height=700");
      } else if (data.status === "already_connected") {
        toast.success("WhatsApp already connected");
      }
    } catch (e: unknown) {
      const err = e as { detail?: string };
      toast.error(err.detail || "Failed to connect WhatsApp.");
    }
    setConnecting(false);
  };

  const handleComplete = async () => {
    try {
      const { data } = await api.post<{ status: string; phone: string }>("/whatsapp/onboarding/complete");
      setWaStatus({ status: data.status, phone: data.phone, app_id: null, connected_at: new Date().toISOString() });
      toast.success(`WhatsApp connected: ${data.phone}`);
    } catch (err) { toast.error(getErrorMessage(err, "Verification failed. Make sure you completed the signup.")); }
  };

  const handleDisconnect = async () => {
    try {
      await api.post("/whatsapp/disconnect");
      setWaStatus({ status: "disconnected", phone: null, app_id: null, connected_at: null });
      toast.success("WhatsApp disconnected");
    } catch { toast.error("Failed to load data"); }
  };

  const isActive = waStatus?.status === "active";

  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <WhatsappLogo className="h-5 w-5 text-whatsapp" weight="fill" />
        <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-text-primary">
          WhatsApp Business
        </h3>
      </div>

      {isActive ? (
        <Card className="p-0">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-whatsapp/10 flex items-center justify-center">
                <WhatsappLogo className="h-5 w-5 text-whatsapp" weight="fill" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text-primary">{waStatus?.phone || "Connected"}</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
                <p className="text-xs text-text-tertiary mt-0.5">
                  {waStatus?.connected_at ? `Connected ${formatRelativeTime(waStatus.connected_at)}` : "WhatsApp Business connected"}
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="text-error" onClick={handleDisconnect}>
              <Trash className="h-4 w-4" />
            </Button>
          </div>
          <div className="border-t border-border px-4 py-3 bg-border-light/30">
            <div className="flex items-center gap-4">
              <span className="text-xs text-text-secondary">Send template messages</span>
              <span className="text-xs text-text-secondary">Receive buyer replies</span>
              <span className="text-xs text-text-secondary">24hr session window</span>
            </div>
          </div>
        </Card>
      ) : waStatus?.status === "onboarding" ? (
        <Card>
          <div className="flex flex-col items-center text-center py-4">
            <WhatsappLogo className="h-8 w-8 text-whatsapp mb-3" weight="fill" />
            <p className="text-sm font-medium text-text-primary mb-1">Complete WhatsApp Setup</p>
            <p className="text-xs text-text-secondary max-w-sm mb-4">
              {embedUrl ? "Complete the signup in the popup window, then click below to verify." : "Setup is in progress."}
            </p>
            <div className="flex gap-2">
              {embedUrl && (
                <Button variant="secondary" size="sm" onClick={() => window.open(embedUrl, "_blank")}>
                  Reopen Signup
                </Button>
              )}
              <Button size="sm" onClick={handleComplete}>
                I've Completed Signup
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="border-dashed">
          <div className="flex flex-col items-center text-center py-6">
            <div className="h-12 w-12 rounded-full bg-whatsapp/10 flex items-center justify-center mb-3">
              <WhatsappLogo className="h-6 w-6 text-whatsapp" weight="fill" />
            </div>
            <p className="text-sm font-medium text-text-primary mb-1">Connect WhatsApp Business</p>
            <p className="text-xs text-text-secondary max-w-sm mb-4">
              Send and receive WhatsApp messages through your own business number. You'll need a phone number and Facebook Business Manager access.
            </p>
            <Button onClick={handleConnect} isLoading={connecting} className="bg-whatsapp hover:bg-green-600 text-white">
              <WhatsappLogo className="h-4 w-4 mr-1" weight="fill" /> Connect WhatsApp
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

const GMAIL_PERMISSIONS = [
  { icon: Eye, label: "Read emails", description: "Read your inbox to identify inbound leads" },
  { icon: PaperPlaneTilt, label: "Send emails", description: "Send and reply to emails on your behalf" },
  { icon: Tag, label: "Manage labels", description: "Organize emails with labels and mark as read" },
];

function IntegrationsContent() {
  const searchParams = useSearchParams();
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnectTarget, setDisconnectTarget] = useState<EmailAccount | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [disconnectConfirmText, setDisconnectConfirmText] = useState("");
  const [showPermissions, setShowPermissions] = useState(false);

  const fetchAccounts = useCallback(async () => {
    try {
      const { data } = await api.get<EmailAccount[]>("/email/accounts");
      setAccounts(data);
    } catch { toast.error("Failed to load data"); }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAccounts();
    // Show toast if just connected
    if (searchParams.get("gmail") === "connected") {
      const email = searchParams.get("email");
      toast.success(`Gmail connected: ${email || "account linked"}`);
      // Clean URL
      window.history.replaceState({}, "", "/settings/integrations");
    }
  }, [fetchAccounts, searchParams]);

  const handleConnectGmail = async () => {
    setConnecting(true);
    try {
      const { data } = await api.get<{ auth_url: string }>("/email/connect/gmail");
      // Redirect to Google OAuth
      window.location.href = data.auth_url;
    } catch (e) {
      toast.error("Failed to start Gmail connection. Check if Google OAuth is configured.");
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!disconnectTarget) return;
    setDisconnecting(true);
    try {
      await api.delete(`/email/accounts/${disconnectTarget.id}`);
      toast.success(`Disconnected ${disconnectTarget.email_address}`);
      setDisconnectTarget(null);
      fetchAccounts();
    } catch (err) { toast.error(getErrorMessage(err, "Failed to disconnect")); }
    setDisconnecting(false);
  };

  const handleSyncNow = async (accountId: string) => {
    try {
      const { data } = await api.get<{ messages: Array<{ id: string }>; result_size_estimate: number }>(
        `/email/accounts/${accountId}/messages?max_results=5`
      );
      toast.success(`Synced: ${data.result_size_estimate} messages found (last 7 days)`);
    } catch (err) { toast.error(getErrorMessage(err, "Sync failed")); }
  };

  const gmailAccounts = accounts.filter((a) => a.provider === "gmail");

  return (
    <AppShell title="Settings">
      <FullWidthLayout>
        <SettingsNav />
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
            Connected Services
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Connect your email and messaging accounts to enable lead capture and outreach.
          </p>
        </div>

        {/* Email Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <EnvelopeSimple className="h-5 w-5 text-text-secondary" />
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-text-primary">
                Email Accounts
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPermissions(true)}
                className="text-xs text-text-tertiary hover:text-text-secondary cursor-pointer"
              >
                What permissions are needed?
              </button>
              <Button onClick={handleConnectGmail} isLoading={connecting} size="sm">
                <GoogleLogo className="h-4 w-4 mr-1" weight="bold" /> Connect Gmail
              </Button>
            </div>
          </div>

          {gmailAccounts.length === 0 && !loading ? (
            <Card className="border-dashed">
              <div className="flex flex-col items-center text-center py-6">
                <div className="h-12 w-12 rounded-full bg-border-light flex items-center justify-center mb-3">
                  <GoogleLogo className="h-6 w-6 text-text-tertiary" weight="bold" />
                </div>
                <p className="text-sm font-medium text-text-primary mb-1">No email accounts connected</p>
                <p className="text-xs text-text-secondary max-w-sm mb-4">
                  Connect your Gmail account to automatically read inbound emails, identify leads,
                  and manage conversations from within TradeCRM.
                </p>
                <Button onClick={handleConnectGmail} isLoading={connecting}>
                  <GoogleLogo className="h-4 w-4 mr-1" weight="bold" /> Connect Gmail Account
                </Button>
              </div>
            </Card>
          ) : (
            <div className="space-y-3">
              {gmailAccounts.map((account) => (
                <Card key={account.id} className="p-0">
                  <div className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-red-50 flex items-center justify-center">
                        <GoogleLogo className="h-5 w-5 text-red-500" weight="bold" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-text-primary">
                            {account.email_address}
                          </span>
                          <Badge variant="success" size="sm">
                            <Check className="h-3 w-3 mr-0.5" weight="bold" /> Connected
                          </Badge>
                        </div>
                        <p className="text-xs text-text-tertiary mt-0.5">
                          Connected {formatRelativeTime(account.created_at)}
                          {account.last_sync_at && ` / Last synced ${formatRelativeTime(account.last_sync_at)}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost" size="sm"
                        onClick={() => handleSyncNow(account.id)}
                      >
                        <ArrowsClockwise className="h-4 w-4 mr-1" /> Sync Now
                      </Button>
                      <Button
                        variant="ghost" size="sm"
                        onClick={() => setDisconnectTarget(account)}
                        className="text-error hover:text-error"
                      >
                        <Trash className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Permissions summary */}
                  <div className="border-t border-border px-4 py-3 bg-border-light/30">
                    <div className="flex items-center gap-4">
                      {GMAIL_PERMISSIONS.map((perm) => (
                        <div key={perm.label} className="flex items-center gap-1.5">
                          <perm.icon className="h-3.5 w-3.5 text-success" />
                          <span className="text-xs text-text-secondary">{perm.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              ))}

              {/* Add another account */}
              <button
                onClick={handleConnectGmail}
                className="w-full p-3 border border-dashed border-border rounded-[var(--radius-md)] text-sm text-text-tertiary hover:text-primary hover:border-primary-lighter transition-colors cursor-pointer"
              >
                + Connect another Gmail account
              </button>
            </div>
          )}
        </div>

        {/* WhatsApp Section (placeholder) */}
        <WhatsAppSection />

        {/* Outlook Section (placeholder) */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <MicrosoftOutlookLogo className="h-5 w-5 text-blue-600" weight="fill" />
            <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-text-primary">
              Microsoft Outlook
            </h3>
          </div>
          <Card className="border-dashed">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-text-primary">Outlook / Office 365</p>
                <p className="text-xs text-text-secondary">
                  Connect your Outlook account for email reading and outreach.
                </p>
              </div>
              <Badge variant="outline" size="md">Coming Soon</Badge>
            </div>
          </Card>
        </div>

        {/* Sync Info */}
        {gmailAccounts.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <ArrowsClockwise className="h-5 w-5 text-text-secondary" />
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-text-primary">
                How Sync Works
              </h3>
            </div>
            <Card>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <ArrowsClockwise className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">Automatic: Twice daily</p>
                    <p className="text-xs text-text-secondary">
                      Emails are automatically checked at 9:00 AM and 5:00 PM (UTC) for all connected accounts.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Eye className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">On-demand: Sync Now</p>
                    <p className="text-xs text-text-secondary">
                      Click "Sync Now" on any account above to immediately check for new emails from the last 7 days.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">Lead detection</p>
                    <p className="text-xs text-text-secondary">
                      On each sync, the AI agent reads new emails, identifies leads, extracts contact and product details, and maps them to your catalog.
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Permissions Info Modal */}
        <Modal
          open={showPermissions}
          onOpenChange={setShowPermissions}
          title="Gmail Permissions"
          size="md"
          footer={<Button onClick={() => setShowPermissions(false)}>Got it</Button>}
        >
          <div className="space-y-4 py-2">
            <p className="text-sm text-text-secondary">
              When you connect Gmail, TradeCRM requests the following permissions:
            </p>
            {GMAIL_PERMISSIONS.map((perm) => (
              <div key={perm.label} className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <perm.icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">{perm.label}</p>
                  <p className="text-xs text-text-secondary">{perm.description}</p>
                </div>
              </div>
            ))}
            <div className="rounded-[var(--radius-md)] bg-border-light p-3 mt-4">
              <div className="flex items-start gap-2">
                <ShieldCheck className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <p className="text-xs text-text-secondary">
                  Your email data is processed securely and never shared with third parties.
                  You can revoke access at any time from this page or from your
                  Google Account settings.
                </p>
              </div>
            </div>
          </div>
        </Modal>

        {/* Disconnect Confirmation */}
        <Modal
          open={!!disconnectTarget}
          onOpenChange={(v) => { if (!v) { setDisconnectTarget(null); setDisconnectConfirmText(""); } }}
          title="Disconnect Email Account"
          size="md"
          footer={
            <>
              <Button variant="secondary" onClick={() => { setDisconnectTarget(null); setDisconnectConfirmText(""); }}>
                Keep Connected
              </Button>
              <Button
                variant="destructive"
                onClick={handleDisconnect}
                isLoading={disconnecting}
                disabled={disconnectConfirmText !== "DISCONNECT"}
              >
                Disconnect Permanently
              </Button>
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
                  Disconnect {disconnectTarget?.email_address}?
                </p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  This action will immediately impact the following workflows:
                </p>
              </div>
            </div>

            <div className="rounded-[var(--radius-md)] border border-error/20 bg-error/5 p-3 mb-4">
              <ul className="text-xs text-text-primary space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-error mt-0.5">-</span>
                  <span><strong>Lead capture will stop</strong> — No new inbound leads will be detected from this email account.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-error mt-0.5">-</span>
                  <span><strong>Auto-sync will stop</strong> — Scheduled email reading (2x daily) will no longer run for this account.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-error mt-0.5">-</span>
                  <span><strong>Replies will fail</strong> — Any pending or draft replies linked to this account cannot be sent.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-error mt-0.5">-</span>
                  <span><strong>Campaign outreach</strong> — Active campaigns using this email for sending will be paused.</span>
                </li>
              </ul>
            </div>

            <p className="text-xs text-text-secondary mb-3">
              Existing leads, contacts, and conversation history will be preserved. You can reconnect this account at any time.
            </p>

            <div>
              <p className="text-xs font-medium text-text-primary mb-1.5">
                Type <span className="font-mono bg-border-light px-1 py-0.5 rounded text-error">DISCONNECT</span> to confirm:
              </p>
              <input
                type="text"
                value={disconnectConfirmText}
                onChange={(e) => setDisconnectConfirmText(e.target.value)}
                placeholder="DISCONNECT"
                className="w-full rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-error/20 focus:border-error"
              />
            </div>
          </div>
        </Modal>
      </FullWidthLayout>
    </AppShell>
  );
}

export default function IntegrationsSettingsPage() {
  return (
    <Suspense fallback={<div />}>
      <IntegrationsContent />
    </Suspense>
  );
}
