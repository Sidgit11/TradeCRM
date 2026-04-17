"use client";

import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { SettingsNav } from "@/components/layout/SettingsNav";
import { EmptyState } from "@/components/ui/EmptyState";
import { CreditCard } from "@phosphor-icons/react";

export default function BillingSettingsPage() {
  return (
    <AppShell title="Settings">
      <FullWidthLayout>
        <SettingsNav />
        <EmptyState
          icon={<CreditCard className="h-12 w-12" />}
          heading="Billing and Subscription"
          description="Manage your plan, usage, and credits."
        />
      </FullWidthLayout>
    </AppShell>
  );
}
