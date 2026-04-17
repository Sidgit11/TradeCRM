"use client";

import { WhatsappLogo, EnvelopeSimple } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { EnrichmentStatusBadge } from "@/components/agentic/EnrichmentStatusBadge";
import type { Contact } from "@/types";

interface ContactCardProps {
  contact: Contact;
  onClick?: () => void;
  className?: string;
}

export function ContactCard({ contact, onClick, className }: ContactCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-[var(--radius-md)] border border-border bg-surface p-4 transition-all hover:shadow-[var(--shadow-md)] cursor-pointer",
        className,
      )}
    >
      <div className="flex items-start justify-between mb-1">
        <div>
          <h4 className="text-sm font-semibold text-text-primary">{contact.name}</h4>
          {contact.title && (
            <p className="text-xs text-text-secondary">{contact.title}</p>
          )}
          {contact.company_name && (
            <p className="text-xs text-text-tertiary">{contact.company_name}</p>
          )}
        </div>
        <EnrichmentStatusBadge status={contact.enrichment_status} />
      </div>

      <div className="flex items-center gap-3 mt-2">
        <WhatsappLogo
          className={cn("h-4 w-4", contact.phone ? "text-whatsapp" : "text-text-tertiary")}
          weight={contact.phone ? "fill" : "regular"}
        />
        <EnvelopeSimple
          className={cn("h-4 w-4", contact.email ? "text-email" : "text-text-tertiary")}
          weight={contact.email ? "fill" : "regular"}
        />
      </div>

      {contact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {contact.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} size="sm" variant="outline">{tag}</Badge>
          ))}
        </div>
      )}
    </div>
  );
}
