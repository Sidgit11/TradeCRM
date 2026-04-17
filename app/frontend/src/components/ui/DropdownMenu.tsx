"use client";

import * as RadixDropdown from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/utils";

interface DropdownMenuProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: "start" | "center" | "end";
}

interface DropdownItemProps {
  children: React.ReactNode;
  icon?: React.ReactNode;
  onSelect?: () => void;
  destructive?: boolean;
}

export function DropdownMenu({ trigger, children, align = "end" }: DropdownMenuProps) {
  return (
    <RadixDropdown.Root>
      <RadixDropdown.Trigger asChild>{trigger}</RadixDropdown.Trigger>
      <RadixDropdown.Portal>
        <RadixDropdown.Content
          align={align}
          sideOffset={4}
          className="z-50 min-w-[180px] rounded-[var(--radius-md)] border border-border bg-surface p-1 shadow-[var(--shadow-lg)] animate-in fade-in-0 zoom-in-95"
        >
          {children}
        </RadixDropdown.Content>
      </RadixDropdown.Portal>
    </RadixDropdown.Root>
  );
}

export function DropdownItem({ children, icon, onSelect, destructive }: DropdownItemProps) {
  return (
    <RadixDropdown.Item
      onSelect={onSelect}
      className={cn(
        "flex items-center gap-2 px-2.5 py-2 text-sm rounded-[var(--radius-sm)] cursor-pointer outline-none transition-colors",
        destructive
          ? "text-error hover:bg-error/10"
          : "text-text-primary hover:bg-border-light",
      )}
    >
      {icon && <span className="text-text-tertiary">{icon}</span>}
      {children}
    </RadixDropdown.Item>
  );
}

export const DropdownSeparator = () => (
  <RadixDropdown.Separator className="h-px my-1 bg-border" />
);
