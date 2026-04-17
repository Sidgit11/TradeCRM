"use client";

import { Bell, Command } from "@phosphor-icons/react";
import { Avatar } from "@/components/ui/Avatar";

interface TopBarProps {
  title: string;
}

export function TopBar({ title }: TopBarProps) {
  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-border bg-surface shrink-0">
      <h1 className="text-lg font-semibold font-[family-name:var(--font-heading)] text-text-primary">
        {title}
      </h1>

      <div className="flex items-center gap-3">
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-sm)] border border-border text-sm text-text-tertiary hover:bg-border-light transition-colors cursor-pointer">
          <Command className="h-3.5 w-3.5" />
          <span>K</span>
        </button>

        <button className="relative p-2 rounded-[var(--radius-sm)] text-text-tertiary hover:bg-border-light transition-colors cursor-pointer">
          <Bell className="h-5 w-5" />
        </button>

        <Avatar name="Dev User" size="sm" />
      </div>
    </header>
  );
}
