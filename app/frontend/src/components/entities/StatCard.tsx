"use client";

import { ArrowUp, ArrowDown } from "@phosphor-icons/react";
import { cn, formatNumber } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number;
  trend?: { direction: "up" | "down"; percentage: number };
  className?: string;
}

export function StatCard({ label, value, trend, className }: StatCardProps) {
  return (
    <div className={cn("rounded-[var(--radius-md)] border border-border bg-surface p-4", className)}>
      <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1">
        {label}
      </p>
      <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
        {formatNumber(value)}
      </p>
      {trend && (
        <div className="flex items-center gap-1 mt-1">
          {trend.direction === "up" ? (
            <ArrowUp className="h-3.5 w-3.5 text-success" weight="bold" />
          ) : (
            <ArrowDown className="h-3.5 w-3.5 text-error" weight="bold" />
          )}
          <span
            className={cn(
              "text-xs font-medium",
              trend.direction === "up" ? "text-green-700" : "text-red-700",
            )}
          >
            {trend.percentage}%
          </span>
          <span className="text-xs text-text-tertiary">vs last week</span>
        </div>
      )}
    </div>
  );
}
