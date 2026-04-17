"use client";

import { cn, formatNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { ConfidenceBadge } from "@/components/agentic/ConfidenceBadge";
import { EnrichmentStatusBadge } from "@/components/agentic/EnrichmentStatusBadge";
import type { Company } from "@/types";

interface CompanyCardProps {
  company: Company;
  variant?: "compact" | "expanded";
  onClick?: () => void;
  className?: string;
}

export function CompanyCard({ company, variant = "compact", onClick, className }: CompanyCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-[var(--radius-md)] border border-border bg-surface p-4 transition-all hover:shadow-[var(--shadow-md)] cursor-pointer",
        className,
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="text-sm font-semibold text-text-primary">{company.name}</h4>
          {company.country && (
            <p className="text-xs text-text-secondary">{company.country}</p>
          )}
        </div>
        <EnrichmentStatusBadge status={company.enrichment_status} />
      </div>

      {company.commodities.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {company.commodities.slice(0, 3).map((commodity) => (
            <Badge key={commodity} size="sm">{commodity}</Badge>
          ))}
          {company.commodities.length > 3 && (
            <Badge size="sm" variant="outline">+{company.commodities.length - 3}</Badge>
          )}
        </div>
      )}

      {company.import_volume_annual && (
        <p className="text-xs text-text-secondary">
          Import Volume: ${formatNumber(company.import_volume_annual)}/yr
        </p>
      )}

      {company.confidence_score !== null && company.confidence_score !== undefined && (
        <div className="mt-2">
          <ConfidenceBadge score={company.confidence_score} />
        </div>
      )}

      {variant === "expanded" && (
        <div className="mt-3 pt-3 border-t border-border space-y-1">
          {company.website && (
            <p className="text-xs text-text-tertiary truncate">{company.website}</p>
          )}
          {company.shipment_frequency && (
            <p className="text-xs text-text-secondary">
              Frequency: {company.shipment_frequency}
            </p>
          )}
          {company.last_shipment_date && (
            <p className="text-xs text-text-secondary">
              Last Shipment: {company.last_shipment_date}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
