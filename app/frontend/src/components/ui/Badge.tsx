"use client";

import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "error" | "info" | "whatsapp" | "email" | "outline";
type BadgeSize = "sm" | "md";

interface BadgeProps {
  variant?: BadgeVariant;
  size?: BadgeSize;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-border-light text-text-secondary",
  success: "bg-success/10 text-green-700",
  warning: "bg-warning/10 text-amber-700",
  error: "bg-error/10 text-red-700",
  info: "bg-info/10 text-blue-700",
  whatsapp: "bg-whatsapp/10 text-green-700",
  email: "bg-email/10 text-blue-700",
  outline: "border border-border text-text-secondary bg-transparent",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "text-[11px] px-1.5 py-0.5",
  md: "text-xs px-2 py-0.5",
};

export function Badge({ variant = "default", size = "sm", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded-[var(--radius-full)]",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
    >
      {children}
    </span>
  );
}
