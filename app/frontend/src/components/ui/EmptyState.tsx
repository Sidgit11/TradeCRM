"use client";

import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface EmptyStateProps {
  icon?: React.ReactNode;
  heading: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon,
  heading,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 px-4 text-center", className)}>
      {icon && <div className="mb-4 text-text-tertiary">{icon}</div>}
      <h3 className="text-lg font-semibold font-[family-name:var(--font-heading)] text-text-primary mb-1">
        {heading}
      </h3>
      {description && (
        <p className="text-sm text-text-secondary max-w-md mb-6">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  );
}
