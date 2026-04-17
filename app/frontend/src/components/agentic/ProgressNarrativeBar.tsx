"use client";

import { Stop } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

interface ProgressNarrativeBarProps {
  text: string;
  isActive?: boolean;
  onStop?: () => void;
  className?: string;
}

export function ProgressNarrativeBar({
  text,
  isActive = true,
  onStop,
  className,
}: ProgressNarrativeBarProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] bg-primary/5 border border-primary/10",
        className,
      )}
    >
      {isActive && (
        <div className="h-2 w-2 rounded-full bg-primary animate-pulse-dot shrink-0" />
      )}
      <p className={cn("text-sm text-text-secondary flex-1 truncate", isActive && "animate-shimmer bg-clip-text")}>
        {text}
      </p>
      {isActive && onStop && (
        <button
          onClick={onStop}
          className="shrink-0 p-1 rounded text-text-tertiary hover:text-error hover:bg-error/10 transition-colors"
        >
          <Stop className="h-4 w-4" weight="fill" />
        </button>
      )}
    </div>
  );
}
