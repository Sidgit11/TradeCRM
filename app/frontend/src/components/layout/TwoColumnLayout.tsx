"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { X } from "@phosphor-icons/react";

interface TwoColumnLayoutProps {
  children: React.ReactNode;
  sidePanel?: React.ReactNode;
  sidePanelOpen?: boolean;
  onCloseSidePanel?: () => void;
  className?: string;
}

export function TwoColumnLayout({
  children,
  sidePanel,
  sidePanelOpen = false,
  onCloseSidePanel,
  className,
}: TwoColumnLayoutProps) {
  return (
    <div className={cn("flex h-full", className)}>
      <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
      {sidePanel && sidePanelOpen && (
        <div className="w-[380px] border-l border-border bg-surface overflow-y-auto shrink-0">
          {onCloseSidePanel && (
            <div className="flex justify-end p-2">
              <button
                onClick={onCloseSidePanel}
                className="p-1 rounded text-text-tertiary hover:bg-border-light cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          {sidePanel}
        </div>
      )}
    </div>
  );
}
