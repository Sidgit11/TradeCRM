"use client";

import { Button } from "@/components/ui/Button";
import { Clock } from "@phosphor-icons/react";

export default function PendingApprovalPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-[480px] text-center">
        <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-10 shadow-[var(--shadow-md)]">
          <div className="flex justify-center mb-6">
            <div className="h-16 w-16 rounded-full bg-warning/10 flex items-center justify-center">
              <Clock className="h-8 w-8 text-warning" weight="fill" />
            </div>
          </div>
          <h1 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary mb-2">
            Access Pending
          </h1>
          <p className="text-sm text-text-secondary mb-6 leading-relaxed">
            Your account has been created but is awaiting approval from the Tradyon team.
          </p>
          <Button variant="secondary" onClick={() => window.location.href = "/login"} className="w-full">
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
}
