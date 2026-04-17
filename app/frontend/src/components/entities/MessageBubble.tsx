"use client";

import { Checks, Check, WhatsappLogo, EnvelopeSimple } from "@phosphor-icons/react";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Message } from "@/types";

interface MessageBubbleProps {
  message: Message;
  className?: string;
}

function DeliveryStatus({ status }: { status: Message["status"] }) {
  switch (status) {
    case "sent":
      return <Check className="h-3 w-3 text-text-tertiary" />;
    case "delivered":
      return <Checks className="h-3 w-3 text-text-tertiary" />;
    case "opened":
      return <Checks className="h-3 w-3 text-info" />;
    default:
      return null;
  }
}

export function MessageBubble({ message, className }: MessageBubbleProps) {
  const isOutbound = message.direction === "outbound";
  const isWhatsApp = message.channel === "whatsapp";

  return (
    <div
      className={cn(
        "flex flex-col max-w-[70%]",
        isOutbound ? "ml-auto items-end" : "mr-auto items-start",
        className,
      )}
    >
      <div
        className={cn(
          "rounded-[var(--radius-lg)] px-3.5 py-2.5 text-sm",
          isOutbound
            ? isWhatsApp
              ? "bg-[#DCF8C6] text-text-primary"
              : "bg-primary/10 text-text-primary"
            : "bg-surface border border-border text-text-primary",
        )}
      >
        {message.channel === "email" && message.subject && (
          <p className="font-semibold text-sm mb-1">{message.subject}</p>
        )}
        <p className="whitespace-pre-wrap">{message.body}</p>
      </div>
      <div className="flex items-center gap-1.5 mt-1 px-1">
        {isWhatsApp ? (
          <WhatsappLogo className="h-3 w-3 text-whatsapp" weight="fill" />
        ) : (
          <EnvelopeSimple className="h-3 w-3 text-email" weight="fill" />
        )}
        <span className="text-[11px] text-text-tertiary">
          {formatRelativeTime(message.created_at)}
        </span>
        {isOutbound && <DeliveryStatus status={message.status} />}
      </div>
    </div>
  );
}
