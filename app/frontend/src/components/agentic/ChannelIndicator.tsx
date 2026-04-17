"use client";

import { WhatsappLogo, EnvelopeSimple } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import type { ChannelType } from "@/types";

interface ChannelIndicatorProps {
  channel: ChannelType;
  className?: string;
}

export function ChannelIndicator({ channel, className }: ChannelIndicatorProps) {
  if (channel === "whatsapp") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-[var(--radius-full)] bg-whatsapp/10 text-green-700",
          className,
        )}
      >
        <WhatsappLogo className="h-3.5 w-3.5" weight="fill" />
        WhatsApp
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-[var(--radius-full)] bg-email/10 text-blue-700",
        className,
      )}
    >
      <EnvelopeSimple className="h-3.5 w-3.5" weight="fill" />
      Email
    </span>
  );
}
