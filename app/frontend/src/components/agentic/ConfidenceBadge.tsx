"use client";

import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  score: number;
  className?: string;
}

export function ConfidenceBadge({ score, className }: ConfidenceBadgeProps) {
  const level = score >= 0.8 ? "high" : score >= 0.5 ? "medium" : "low";
  const config = {
    high: { label: "High", dotClass: "bg-success", textClass: "text-green-700" },
    medium: { label: "Medium", dotClass: "bg-warning", textClass: "text-amber-700" },
    low: { label: "Low", dotClass: "bg-error", textClass: "text-red-700" },
  };

  const { label, dotClass, textClass } = config[level];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", textClass, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClass)} />
      {label}
    </span>
  );
}
