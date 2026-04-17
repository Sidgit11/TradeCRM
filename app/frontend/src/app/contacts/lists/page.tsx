"use client";

import { AppShell } from "@/components/layout/AppShell";
import { FullWidthLayout } from "@/components/layout/FullWidthLayout";
import { EmptyState } from "@/components/ui/EmptyState";
import { ListBullets } from "@phosphor-icons/react";

export default function ContactListsPage() {
  return (
    <AppShell title="Contact Lists">
      <FullWidthLayout>
        <EmptyState
          icon={<ListBullets className="h-12 w-12" />}
          heading="No contact lists yet"
          description="Organize your contacts into lists for targeted campaigns."
          actionLabel="Create List"
          onAction={() => {}}
        />
      </FullWidthLayout>
    </AppShell>
  );
}
