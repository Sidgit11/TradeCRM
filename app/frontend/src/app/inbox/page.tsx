"use client";
import type { MessageTemplate } from "@/types";

import { useState, useEffect, useCallback, useRef } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  ChatCircleDots, WhatsappLogo, EnvelopeSimple, User,
  PaperPlaneRight, Sparkle, FileText, Buildings, Phone,
  ArrowRight,
} from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";
import { toast } from "sonner";
import { formatRelativeTime } from "@/lib/utils";

interface Conversation {
  contact_id: string;
  contact_name: string;
  company_name: string | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  channel: string;
  unread_count: number;
  classification: string | null;
}

interface ThreadMessage {
  id: string;
  direction: string;
  channel: string;
  body: string;
  subject: string | null;
  status: string;
  created_at: string;
  sender_name: string | null;
}

export default function InboxPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [thread, setThread] = useState<ThreadMessage[]>([]);
  const [threadLoading, setThreadLoading] = useState(false);

  // Composer
  const [replyChannel, setReplyChannel] = useState<"email" | "whatsapp">("email");
  const [replySubject, setReplySubject] = useState("");
  const [replyBody, setReplyBody] = useState("");
  const [sending, setSending] = useState(false);
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [showTemplates, setShowTemplates] = useState(false);
  const threadEndRef = useRef<HTMLDivElement>(null);

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Conversation[]>("/inbox/conversations");
      setConversations(data);
    } catch { toast.error("Failed to load inbox"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  // Fetch templates
  useEffect(() => {
    api.get<MessageTemplate[]>("/templates").then(({ data }) => setTemplates(data)).catch(() => {});
  }, []);

  // Fetch thread when active conversation changes
  useEffect(() => {
    if (!activeId) return;
    setThreadLoading(true);
    api.get<ThreadMessage[]>(`/inbox/conversations/${activeId}`).then(({ data }) => {
      setThread(data);
      setTimeout(() => threadEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }).catch(() => toast.error("Failed to load thread")).finally(() => setThreadLoading(false));
  }, [activeId]);

  const activeConvo = conversations.find((c) => c.contact_id === activeId);

  const handleSendReply = async () => {
    if (!activeId || !replyBody.trim()) { toast.error("Message cannot be empty"); return; }
    setSending(true);
    try {
      await api.post(`/inbox/conversations/${activeId}/reply`, {
        channel: replyChannel,
        body: replyBody.trim(),
        subject: replyChannel === "email" ? replySubject.trim() || null : null,
      });
      toast.success("Message sent");
      setReplyBody(""); setReplySubject("");
      // Refresh thread
      const { data } = await api.get<ThreadMessage[]>(`/inbox/conversations/${activeId}`);
      setThread(data);
      setTimeout(() => threadEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (err) { toast.error(getErrorMessage(err, "Failed to send")); }
    setSending(false);
  };

  const applyTemplate = (t: MessageTemplate) => {
    setReplyBody(t.body);
    if (t.subject && replyChannel === "email") setReplySubject(t.subject);
    setShowTemplates(false);
    toast.success(`Applied: ${t.name}`);
  };

  return (
    <AppShell title="Inbox">
      <ThreeColumnLayout
        left={
          <div className="h-full flex flex-col">
            <div className="p-3 border-b border-border">
              <h3 className="text-sm font-semibold text-text-primary">Conversations</h3>
              <p className="text-[10px] text-text-tertiary">{conversations.length} threads</p>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="p-3 space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} variant="card" className="h-14" />)}</div>
              ) : conversations.length === 0 ? (
                <div className="p-4 text-center">
                  <p className="text-xs text-text-tertiary">No conversations yet</p>
                </div>
              ) : (
                conversations.map((c) => (
                  <button key={c.contact_id} onClick={() => { setActiveId(c.contact_id); setReplyChannel(c.channel === "whatsapp" ? "whatsapp" : "email"); }}
                    className={`w-full text-left px-3 py-2.5 border-b border-border transition-colors cursor-pointer ${
                      activeId === c.contact_id ? "bg-primary/5" : "hover:bg-border-light"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-sm font-medium text-text-primary truncate flex-1">{c.contact_name}</span>
                      <div className="flex items-center gap-1 shrink-0">
                        {c.unread_count > 0 && (
                          <span className="min-w-[16px] h-4 px-1 flex items-center justify-center rounded-full bg-error text-text-inverse text-[9px] font-bold">{c.unread_count}</span>
                        )}
                        {c.channel === "whatsapp" ? <WhatsappLogo className="h-3 w-3 text-whatsapp" /> : c.channel === "email" ? <EnvelopeSimple className="h-3 w-3 text-primary" /> : null}
                      </div>
                    </div>
                    {c.company_name && <p className="text-[10px] text-text-tertiary truncate">{c.company_name}</p>}
                    {c.last_message_preview && <p className="text-xs text-text-secondary truncate mt-0.5">{c.last_message_preview}</p>}
                    <div className="flex items-center justify-between mt-0.5">
                      {c.classification && <Badge size="sm" variant={c.classification === "interested" ? "success" : "outline"}>{c.classification}</Badge>}
                      {c.last_message_at && <span className="text-[9px] text-text-tertiary">{formatRelativeTime(c.last_message_at)}</span>}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        }
        center={
          !activeId ? (
            <EmptyState
              icon={<ChatCircleDots className="h-12 w-12" />}
              heading="Select a conversation"
              description="Click on a conversation from the left panel to view the message thread."
            />
          ) : (
            <div className="h-full flex flex-col">
              {/* Thread header */}
              <div className="p-3 border-b border-border flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-text-primary">{activeConvo?.contact_name}</p>
                  {activeConvo?.company_name && <p className="text-xs text-text-tertiary">{activeConvo.company_name}</p>}
                </div>
                <a href={`/contacts/${activeId}`} className="text-xs text-primary hover:underline flex items-center gap-0.5">
                  View Profile <ArrowRight className="h-3 w-3" />
                </a>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {threadLoading ? (
                  <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} variant="card" className="h-16" />)}</div>
                ) : thread.length === 0 ? (
                  <p className="text-xs text-text-tertiary text-center py-4">No messages in this thread</p>
                ) : (
                  thread.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.direction === "outbound" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[75%] rounded-[var(--radius-md)] px-3 py-2 ${
                        msg.direction === "outbound"
                          ? "bg-primary/10 text-text-primary"
                          : msg.channel === "whatsapp" ? "bg-green-50 dark:bg-green-950/30 text-text-primary" : "bg-surface border border-border text-text-primary"
                      }`}>
                        {msg.subject && <p className="text-[10px] font-medium text-text-secondary mb-0.5">{msg.subject}</p>}
                        <p className="text-sm whitespace-pre-wrap">{msg.body}</p>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-[9px] text-text-tertiary">{formatRelativeTime(msg.created_at)}</span>
                          <div className="flex items-center gap-1">
                            {msg.channel === "whatsapp" ? <WhatsappLogo className="h-2.5 w-2.5 text-whatsapp" /> : <EnvelopeSimple className="h-2.5 w-2.5 text-primary" />}
                            <Badge size="sm" variant="outline" className="text-[8px] px-1 py-0">{msg.status}</Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
                <div ref={threadEndRef} />
              </div>

              {/* Composer */}
              <div className="border-t border-border p-3">
                {/* Channel tabs */}
                <div className="flex items-center gap-2 mb-2">
                  <button onClick={() => setReplyChannel("email")}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-sm)] text-xs transition-colors cursor-pointer ${
                      replyChannel === "email" ? "bg-primary/10 text-primary font-medium" : "text-text-secondary hover:text-text-primary"
                    }`}><EnvelopeSimple className="h-3.5 w-3.5" /> Email</button>
                  <button onClick={() => setReplyChannel("whatsapp")}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-sm)] text-xs transition-colors cursor-pointer ${
                      replyChannel === "whatsapp" ? "bg-green-100 text-whatsapp font-medium" : "text-text-secondary hover:text-text-primary"
                    }`}><WhatsappLogo className="h-3.5 w-3.5" /> WhatsApp</button>

                  <div className="flex-1" />

                  {/* Template picker */}
                  <div className="relative">
                    <button onClick={() => setShowTemplates(!showTemplates)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-[var(--radius-sm)] text-xs border border-border text-text-secondary hover:text-primary hover:border-primary/30 transition-colors cursor-pointer">
                      <FileText className="h-3.5 w-3.5" /> Templates
                    </button>
                    {showTemplates && (
                      <div className="absolute bottom-full right-0 mb-1 w-72 rounded-[var(--radius-md)] border border-border bg-surface shadow-[var(--shadow-lg)] max-h-[250px] overflow-y-auto py-1 z-20">
                        {templates.filter((t) => t.channel === replyChannel).length === 0 ? (
                          <p className="text-xs text-text-tertiary px-3 py-3 text-center">
                            No {replyChannel} templates yet. <a href="/settings/templates/new" className="text-primary hover:underline">Create one</a>
                          </p>
                        ) : (
                          templates.filter((t) => t.channel === replyChannel).map((t) => (
                            <button key={t.id} onClick={() => applyTemplate(t)}
                              className="w-full text-left px-3 py-2 hover:bg-border-light transition-colors cursor-pointer border-b border-border last:border-0">
                              <p className="text-sm font-medium text-text-primary">{t.name}</p>
                              <p className="text-xs text-text-secondary truncate">{t.body.slice(0, 60)}...</p>
                            </button>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Email subject */}
                {replyChannel === "email" && (
                  <Input inputSize="sm" placeholder="Subject..." value={replySubject} onChange={(e) => setReplySubject(e.target.value)} className="mb-2" />
                )}

                {/* Body + Send */}
                <div className="flex gap-2">
                  <textarea
                    value={replyBody} onChange={(e) => setReplyBody(e.target.value)}
                    placeholder={replyChannel === "whatsapp" ? "Type a WhatsApp message..." : "Type an email reply..."}
                    rows={2}
                    className="flex-1 text-sm rounded-[var(--radius-sm)] border border-border px-3 py-2 bg-surface text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendReply(); } }}
                  />
                  <Button onClick={handleSendReply} isLoading={sending} disabled={!replyBody.trim()} className="self-end">
                    <PaperPlaneRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )
        }
        right={
          activeId && activeConvo ? (
            <div className="p-4 space-y-4">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                  <User className="h-6 w-6 text-primary" />
                </div>
                <p className="text-sm font-semibold text-text-primary">{activeConvo.contact_name}</p>
                {activeConvo.company_name && (
                  <p className="text-xs text-text-secondary flex items-center justify-center gap-1 mt-0.5">
                    <Buildings className="h-3 w-3" /> {activeConvo.company_name}
                  </p>
                )}
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-text-secondary">
                  <span>Channel</span>
                  <span className="font-medium text-text-primary capitalize">{activeConvo.channel}</span>
                </div>
                <div className="flex justify-between text-text-secondary">
                  <span>Unread</span>
                  <span className="font-medium text-text-primary">{activeConvo.unread_count}</span>
                </div>
                {activeConvo.classification && (
                  <div className="flex justify-between text-text-secondary">
                    <span>Classification</span>
                    <Badge size="sm" variant="outline">{activeConvo.classification}</Badge>
                  </div>
                )}
              </div>

              <a href={`/contacts/${activeId}`}
                className="block w-full text-center px-3 py-2 text-xs text-primary border border-primary/20 rounded-[var(--radius-sm)] hover:bg-primary/5 transition-colors">
                View Full Profile
              </a>
            </div>
          ) : (
            <div className="p-4 text-center">
              <p className="text-xs text-text-tertiary">Select a conversation to see contact details</p>
            </div>
          )
        }
      />
    </AppShell>
  );
}
