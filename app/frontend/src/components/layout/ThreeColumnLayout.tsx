"use client";

import { cn } from "@/lib/utils";

interface ThreeColumnLayoutProps {
  left: React.ReactNode;
  center: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
}

export function ThreeColumnLayout({
  left,
  center,
  right,
  className,
}: ThreeColumnLayoutProps) {
  return (
    <div className={cn("flex h-full", className)}>
      <div className="w-[280px] border-r border-border overflow-y-auto shrink-0">
        {left}
      </div>
      <div className="flex-1 overflow-y-auto">{center}</div>
      {right && (
        <div className="w-[320px] border-l border-border overflow-y-auto shrink-0">
          {right}
        </div>
      )}
    </div>
  );
}
