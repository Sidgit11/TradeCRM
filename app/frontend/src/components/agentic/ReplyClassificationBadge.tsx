"use client";

import { cn } from "@/lib/utils";
import type { ReplyClassification } from "@/types";

interface ReplyClassificationBadgeProps {
  classification: ReplyClassification;
  className?: string;
}

const config: Record<ReplyClassification, { label: string; className: string }> = {
  interested: { label: "Interested", className: "bg-success/10 text-green-700" },
  price_inquiry: { label: "Price Inquiry", className: "bg-info/10 text-blue-700" },
  sample_request: { label: "Sample Request", className: "bg-purple-100 text-purple-700" },
  meeting_request: { label: "Meeting Request", className: "bg-teal-100 text-teal-700" },
  not_interested: { label: "Not Interested", className: "bg-gray-100 text-gray-600" },
  auto_reply: { label: "Auto Reply", className: "bg-gray-50 text-gray-500" },
  out_of_office: { label: "Out of Office", className: "bg-amber-50 text-amber-700" },
};

export function ReplyClassificationBadge({ classification, className }: ReplyClassificationBadgeProps) {
  const { label, className: badgeClass } = config[classification];

  return (
    <span
      className={cn(
        "inline-flex items-center text-[11px] font-medium px-2 py-0.5 rounded-[var(--radius-full)]",
        badgeClass,
        className,
      )}
    >
      {label}
    </span>
  );
}
