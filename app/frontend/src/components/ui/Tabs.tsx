"use client";

import * as RadixTabs from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

interface Tab {
  value: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ tabs, defaultValue, value, onValueChange, children, className }: TabsProps) {
  return (
    <RadixTabs.Root
      defaultValue={defaultValue || tabs[0]?.value}
      value={value}
      onValueChange={onValueChange}
      className={className}
    >
      <RadixTabs.List className="flex border-b border-border">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.value}
            value={tab.value}
            className={cn(
              "px-4 py-2.5 text-sm font-medium text-text-secondary border-b-2 border-transparent transition-colors",
              "hover:text-text-primary",
              "data-[state=active]:text-primary data-[state=active]:border-primary",
            )}
          >
            {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {children}
    </RadixTabs.Root>
  );
}

export const TabContent = RadixTabs.Content;
