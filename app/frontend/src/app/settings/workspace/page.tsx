"use client";

import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { SettingsNav } from "@/components/layout/SettingsNav";
import { EmptyState } from "@/components/ui/EmptyState";
import { Gear } from "@phosphor-icons/react";

export default function WorkspaceSettingsPage() {
  return (
    <AppShell title="Settings">
      <FullWidthLayout>
        <SettingsNav />
        <EmptyState
          icon={<Gear className="h-12 w-12" />}
          heading="Workspace Settings"
          description="Configure your company profile, commodities, target markets, and certifications."
        />
      </FullWidthLayout>
    </AppShell>
  );
}
