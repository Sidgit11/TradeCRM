"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps {
  variant?: "text" | "circle" | "card" | "table-row";
  className?: string;
}

export function Skeleton({ variant = "text", className }: SkeletonProps) {
  const styles = {
    text: "h-4 w-full rounded",
    circle: "h-10 w-10 rounded-full",
    card: "h-32 w-full rounded-[var(--radius-md)]",
    "table-row": "h-12 w-full rounded",
  };

  return (
    <div className={cn("animate-shimmer", styles[variant], className)} />
  );
}
