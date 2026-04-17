"use client";

import { Check, X, CircleNotch } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import type { AgentStepStatus } from "@/types";

interface Step {
  name: string;
  status: AgentStepStatus;
  detail?: string | null;
  duration?: string;
}

interface AgentStepTimelineProps {
  steps: Step[];
  className?: string;
}

function StepIcon({ status }: { status: AgentStepStatus }) {
  switch (status) {
    case "completed":
      return (
        <div className="flex items-center justify-center h-6 w-6 rounded-full bg-success text-text-inverse">
          <Check className="h-3.5 w-3.5" weight="bold" />
        </div>
      );
    case "active":
      return (
        <div className="flex items-center justify-center h-6 w-6 rounded-full bg-primary animate-pulse-dot">
          <CircleNotch className="h-3.5 w-3.5 text-text-inverse animate-spin" />
        </div>
      );
    case "failed":
      return (
        <div className="flex items-center justify-center h-6 w-6 rounded-full bg-error text-text-inverse">
          <X className="h-3.5 w-3.5" weight="bold" />
        </div>
      );
    default:
      return (
        <div className="flex items-center justify-center h-6 w-6 rounded-full border-2 border-border bg-surface" />
      );
  }
}

export function AgentStepTimeline({ steps, className }: AgentStepTimelineProps) {
  return (
    <div className={cn("space-y-0", className)}>
      {steps.map((step, index) => (
        <div key={index} className="flex gap-3">
          <div className="flex flex-col items-center">
            <StepIcon status={step.status} />
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "w-px flex-1 min-h-[24px]",
                  step.status === "completed" ? "bg-success" : "bg-border",
                )}
              />
            )}
          </div>
          <div className="pb-4 pt-0.5 min-w-0">
            <p
              className={cn(
                "text-sm",
                step.status === "active" && "font-medium text-text-primary",
                step.status === "completed" && "text-text-secondary",
                step.status === "pending" && "text-text-tertiary",
                step.status === "failed" && "text-error",
              )}
            >
              {step.name}
            </p>
            {step.detail && (
              <p className="text-xs text-text-tertiary mt-0.5">{step.detail}</p>
            )}
            {step.duration && (
              <p className="text-xs text-text-tertiary mt-0.5">{step.duration}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
