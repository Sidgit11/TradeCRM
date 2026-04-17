"use client";

import * as RadixTooltip from "@radix-ui/react-tooltip";

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
}

export function Tooltip({ content, children, side = "top" }: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={300}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={4}
            className="z-50 px-2.5 py-1.5 text-xs text-text-inverse bg-text-primary rounded-[var(--radius-sm)] shadow-[var(--shadow-md)] animate-in fade-in-0 zoom-in-95"
          >
            {content}
            <RadixTooltip.Arrow className="fill-[var(--color-text-primary)]" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
