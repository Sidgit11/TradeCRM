"use client";

import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { Button } from "@/components/ui/Button";
import { MagnifyingGlass, PaperPlaneTilt, ChatCircleDots } from "@phosphor-icons/react";

export default function DashboardPage() {
  const router = useRouter();

  return (
    <AppShell title="Dashboard">
      <FullWidthLayout>
        <div className="py-12 flex flex-col items-center text-center">
          <h2 className="text-2xl font-bold font-[family-name:var(--font-heading)] text-text-primary mb-2">
            Welcome to TradeCRM
          </h2>
          <p className="text-sm text-text-secondary max-w-md mb-8">
            Your command center for outreach campaigns, buyer discovery, and deal tracking.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl">
            <button
              onClick={() => router.push("/discover")}
              className="flex flex-col items-center gap-3 p-6 rounded-[var(--radius-md)] border border-border bg-surface hover:shadow-[var(--shadow-md)] hover:border-primary-lighter transition-all cursor-pointer"
            >
              <MagnifyingGlass className="h-8 w-8 text-primary" />
              <span className="text-sm font-medium text-text-primary">Find Buyers</span>
              <span className="text-xs text-text-tertiary">Discover importers globally</span>
            </button>

            <button
              onClick={() => router.push("/campaigns/new")}
              className="flex flex-col items-center gap-3 p-6 rounded-[var(--radius-md)] border border-border bg-surface hover:shadow-[var(--shadow-md)] hover:border-primary-lighter transition-all cursor-pointer"
            >
              <PaperPlaneTilt className="h-8 w-8 text-primary" />
              <span className="text-sm font-medium text-text-primary">New Campaign</span>
              <span className="text-xs text-text-tertiary">Multi-channel outreach</span>
            </button>

            <button
              onClick={() => router.push("/inbox")}
              className="flex flex-col items-center gap-3 p-6 rounded-[var(--radius-md)] border border-border bg-surface hover:shadow-[var(--shadow-md)] hover:border-primary-lighter transition-all cursor-pointer"
            >
              <ChatCircleDots className="h-8 w-8 text-primary" />
              <span className="text-sm font-medium text-text-primary">View Inbox</span>
              <span className="text-xs text-text-tertiary">Manage conversations</span>
            </button>
          </div>
        </div>
      </FullWidthLayout>
    </AppShell>
  );
}
