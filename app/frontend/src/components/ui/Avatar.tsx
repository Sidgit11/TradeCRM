"use client";

import { cn, getInitials } from "@/lib/utils";

type AvatarSize = "sm" | "md" | "lg";

interface AvatarProps {
  name: string;
  src?: string | null;
  size?: AvatarSize;
  statusDot?: "online" | "offline" | "busy";
  className?: string;
}

const sizeStyles: Record<AvatarSize, string> = {
  sm: "h-7 w-7 text-[11px]",
  md: "h-9 w-9 text-xs",
  lg: "h-12 w-12 text-sm",
};

const dotSizeStyles: Record<AvatarSize, string> = {
  sm: "h-2 w-2",
  md: "h-2.5 w-2.5",
  lg: "h-3 w-3",
};

const dotColorStyles = {
  online: "bg-success",
  offline: "bg-text-tertiary",
  busy: "bg-error",
};

export function Avatar({ name, src, size = "md", statusDot, className }: AvatarProps) {
  return (
    <div className={cn("relative inline-flex shrink-0", className)}>
      {src ? (
        <img
          src={src}
          alt={name}
          className={cn(
            "rounded-[var(--radius-full)] object-cover",
            sizeStyles[size],
          )}
        />
      ) : (
        <div
          className={cn(
            "rounded-[var(--radius-full)] bg-primary-lighter text-text-inverse flex items-center justify-center font-medium",
            sizeStyles[size],
          )}
        >
          {getInitials(name)}
        </div>
      )}
      {statusDot && (
        <span
          className={cn(
            "absolute bottom-0 right-0 rounded-full border-2 border-surface",
            dotSizeStyles[size],
            dotColorStyles[statusDot],
          )}
        />
      )}
    </div>
  );
}
