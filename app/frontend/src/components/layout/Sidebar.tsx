"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  House,
  MagnifyingGlass,
  Buildings,
  AddressBook,
  PaperPlaneTilt,
  ChatCircleDots,
  Kanban,
  Package,
  UserFocus,
  Gear,
  CaretLeft,
  CaretRight,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { useInboxStore } from "@/stores/inbox-store";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  badge?: number;
  comingSoon?: boolean;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: House, comingSoon: true },
  { label: "Discover", href: "/discover", icon: MagnifyingGlass },
  { label: "Companies", href: "/companies", icon: Buildings },
  { label: "Contacts", href: "/contacts", icon: AddressBook },
  { label: "Campaigns", href: "/campaigns", icon: PaperPlaneTilt },
  { label: "Inbox", href: "/inbox", icon: ChatCircleDots },
  { label: "Opportunities", href: "/opportunities", icon: Kanban },
  { label: "Leads", href: "/leads", icon: UserFocus },
  { label: "Catalog", href: "/catalog", icon: Package },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const unreadTotal = useInboxStore((s) => s.unreadTotal);

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-surface border-r border-border transition-all duration-200",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <div className="flex items-center h-14 px-4 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-[var(--radius-sm)] bg-primary flex items-center justify-center text-text-inverse font-bold text-sm font-[family-name:var(--font-heading)]">
            T
          </div>
          {!collapsed && (
            <span className="text-lg font-bold text-primary font-[family-name:var(--font-heading)]">
              TradeCRM
            </span>
          )}
        </Link>
      </div>

      <nav className="flex-1 py-2 px-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          const badge = item.label === "Inbox" ? unreadTotal : undefined;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)] text-sm transition-colors",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-text-secondary hover:bg-border-light hover:text-text-primary",
                collapsed && "justify-center px-2",
              )}
            >
              <Icon className="h-5 w-5 shrink-0" weight={isActive ? "fill" : "regular"} />
              {!collapsed && (
                <>
                  <span className="flex-1">{item.label}</span>
                  {item.comingSoon && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-border text-text-tertiary font-medium">Soon</span>
                  )}
                  {badge !== undefined && badge > 0 && (
                    <span className="min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-error text-text-inverse text-[10px] font-bold">
                      {badge > 99 ? "99+" : badge}
                    </span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border py-2 px-2 space-y-0.5">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)] text-sm text-text-secondary hover:bg-border-light hover:text-text-primary transition-colors",
            pathname.startsWith("/settings") && "bg-primary/10 text-primary font-medium",
            collapsed && "justify-center px-2",
          )}
        >
          <Gear className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </Link>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)] text-sm text-text-tertiary hover:bg-border-light hover:text-text-secondary transition-colors w-full cursor-pointer"
        >
          {collapsed ? (
            <CaretRight className="h-5 w-5 shrink-0 mx-auto" />
          ) : (
            <>
              <CaretLeft className="h-5 w-5 shrink-0" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
