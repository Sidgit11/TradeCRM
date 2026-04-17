"use client";

import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  selected?: boolean;
  loading?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, hoverable, selected, loading, children, ...props }, ref) => {
    if (loading) {
      return (
        <div
          ref={ref}
          className={cn(
            "rounded-[var(--radius-md)] border border-border bg-surface p-4 animate-shimmer",
            className,
          )}
          {...props}
        >
          <div className="space-y-3">
            <div className="h-4 w-3/4 rounded bg-border-light" />
            <div className="h-3 w-1/2 rounded bg-border-light" />
            <div className="h-3 w-2/3 rounded bg-border-light" />
          </div>
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-[var(--radius-md)] border border-border bg-surface p-4 transition-all",
          hoverable && "hover:shadow-[var(--shadow-md)] cursor-pointer",
          selected && "border-primary ring-1 ring-primary/20",
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );
  },
);

Card.displayName = "Card";
