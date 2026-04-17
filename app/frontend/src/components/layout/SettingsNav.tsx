"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Gear, Plugs, Users, CreditCard, Sliders, FileText } from "@phosphor-icons/react";

const settingsTabs = [
  { label: "Workspace", href: "/settings/workspace", icon: Gear },
  { label: "Templates", href: "/settings/templates", icon: FileText },
  { label: "Integrations", href: "/settings/integrations", icon: Plugs },
  { label: "Personalize", href: "/settings/personalize", icon: Sliders },
  { label: "Team", href: "/settings/team", icon: Users },
  { label: "Billing", href: "/settings/billing", icon: CreditCard },
];

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <div className="border-b border-border mb-6">
      <nav className="flex gap-1">
        {settingsTabs.map((tab) => {
          const isActive = pathname === tab.href;
          const Icon = tab.icon;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors",
                isActive
                  ? "border-primary text-primary font-medium"
                  : "border-transparent text-text-secondary hover:text-text-primary",
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
