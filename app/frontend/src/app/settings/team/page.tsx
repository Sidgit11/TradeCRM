"use client";

import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { SettingsNav } from "@/components/layout/SettingsNav";
import { EmptyState } from "@/components/ui/EmptyState";
import { Users } from "@phosphor-icons/react";

export default function TeamSettingsPage() {
  return (
    <AppShell title="Settings">
      <FullWidthLayout>
        <SettingsNav />
        <EmptyState
          icon={<Users className="h-12 w-12" />}
          heading="Team Management"
          description="Invite team members and manage roles."
        />
      </FullWidthLayout>
    </AppShell>
  );
}
