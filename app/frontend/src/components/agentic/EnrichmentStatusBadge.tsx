"use client";

import { Check, CircleNotch } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import type { EnrichmentStatus } from "@/types";

interface EnrichmentStatusBadgeProps {
  status: EnrichmentStatus;
  className?: string;
}

const config: Record<EnrichmentStatus, { label: string; className: string; icon?: React.ReactNode }> = {
  not_enriched: { label: "Not Enriched", className: "border border-border text-text-tertiary" },
  enriching: {
    label: "Enriching",
    className: "bg-primary/10 text-primary animate-shimmer",
    icon: <CircleNotch className="h-3 w-3 animate-spin" />,
  },
  partially_enriched: { label: "Partial", className: "bg-warning/10 text-amber-700" },
  enriched: {
    label: "Enriched",
    className: "bg-success/10 text-green-700",
    icon: <Check className="h-3 w-3" weight="bold" />,
  },
};

export function EnrichmentStatusBadge({ status, className }: EnrichmentStatusBadgeProps) {
  const { label, className: statusClass, icon } = config[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-[var(--radius-full)]",
        statusClass,
        className,
      )}
    >
      {icon}
      {label}
    </span>
  );
}
