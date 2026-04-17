"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, Check, CircleNotch, MagnifyingGlass, Globe,
  Brain, UsersFour, SealCheck, Warning, Sparkle,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { AgentStepStatus } from "@/types";

interface EnrichmentStep {
  name: string;
  status: AgentStepStatus;
  detail: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface EnrichStatusResponse {
  agent_task_id: string;
  company_id: string;
  status: string;
  steps: EnrichmentStep[];
  fields_populated?: number;
  enrichments_remaining?: number;
}

interface EnrichmentPanelProps {
  companyId: string;
  companyName: string;
  agentTaskId: string;
  enrichmentsRemaining: number | null;
  onClose: () => void;
  onComplete: () => void;
}

const STEP_ICONS = [MagnifyingGlass, Globe, Brain, UsersFour, SealCheck];

const STEP_LABELS = [
  "Searching the web for company info",
  "Scraping website & checking trade directories",
  "Analyzing company data with AI",
  "Discovering decision makers & contacts",
  "Finalizing company profile",
];

function StepIndicator({ status, index }: { status: AgentStepStatus; index: number }) {
  const Icon = STEP_ICONS[index] || MagnifyingGlass;

  if (status === "completed") {
    return (
      <motion.div
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 15 }}
        className="flex items-center justify-center h-8 w-8 rounded-full bg-success text-text-inverse"
      >
        <Check className="h-4 w-4" weight="bold" />
      </motion.div>
    );
  }

  if (status === "active") {
    return (
      <motion.div
        initial={{ scale: 0.8 }}
        animate={{ scale: [1, 1.08, 1] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        className="flex items-center justify-center h-8 w-8 rounded-full bg-primary"
      >
        <CircleNotch className="h-4 w-4 text-text-inverse animate-spin" />
      </motion.div>
    );
  }

  if (status === "failed") {
    return (
      <div className="flex items-center justify-center h-8 w-8 rounded-full bg-error text-text-inverse">
        <Warning className="h-4 w-4" weight="bold" />
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-8 w-8 rounded-full border-2 border-border bg-surface">
      <Icon className="h-3.5 w-3.5 text-text-tertiary" />
    </div>
  );
}

export function EnrichmentPanel({
  companyId,
  companyName,
  agentTaskId,
  enrichmentsRemaining,
  onClose,
  onComplete,
}: EnrichmentPanelProps) {
  const [steps, setSteps] = useState<EnrichmentStep[]>(
    STEP_LABELS.map((name) => ({
      name,
      status: "pending" as AgentStepStatus,
      detail: null,
      started_at: null,
      completed_at: null,
    })),
  );
  const [taskStatus, setTaskStatus] = useState<string>("running");
  const [fieldsPopulated, setFieldsPopulated] = useState<number | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  const pollStatus = useCallback(async () => {
    try {
      const { data } = await api.get<EnrichStatusResponse>(
        `/companies/${companyId}/enrich/status`,
      );

      if (!isMountedRef.current) return;

      if (data.steps && data.steps.length > 0) {
        setSteps(data.steps);
      }
      setTaskStatus(data.status);

      if (data.status === "completed") {
        setFieldsPopulated(data.fields_populated ?? null);
        setShowSuccess(true);

        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }

        setTimeout(() => {
          if (isMountedRef.current) {
            onComplete();
          }
        }, 2500);
      }

      if (data.status === "failed") {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
        toast.error("Enrichment failed. Please try again.");
      }
    } catch {
      // Silently retry on network errors
    }
  }, [companyId, onComplete]);

  useEffect(() => {
    isMountedRef.current = true;

    // First poll immediately
    pollStatus();

    // Then poll every 2 seconds
    pollRef.current = setInterval(pollStatus, 2000);

    return () => {
      isMountedRef.current = false;
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [pollStatus]);

  const completedCount = steps.filter((s) => s.status === "completed").length;
  const progress = (completedCount / steps.length) * 100;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/40 z-50"
        onClick={taskStatus === "completed" || taskStatus === "failed" ? onClose : undefined}
      />
      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed right-0 top-0 bottom-0 w-full max-w-[420px] bg-surface z-50 shadow-[var(--shadow-xl)] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Sparkle className="h-5 w-5 text-primary" weight="fill" />
            <div>
              <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-text-primary">
                Enriching Company
              </h3>
              <p className="text-xs text-text-secondary truncate max-w-[260px]">{companyName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-[var(--radius-sm)] p-1 text-text-tertiary hover:text-text-primary hover:bg-border-light transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="px-6 pt-4 pb-2">
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-xs text-text-tertiary">
              {taskStatus === "completed"
                ? "Enrichment complete"
                : taskStatus === "failed"
                  ? "Enrichment failed"
                  : `Step ${Math.min(completedCount + 1, steps.length)} of ${steps.length}`}
            </p>
            {enrichmentsRemaining !== null && (
              <p className="text-xs text-text-tertiary">
                {enrichmentsRemaining} credits remaining
              </p>
            )}
          </div>
          <div className="h-1.5 rounded-full bg-border-light overflow-hidden">
            <motion.div
              className={cn(
                "h-full rounded-full",
                taskStatus === "failed" ? "bg-error" : "bg-primary",
              )}
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            />
          </div>
        </div>

        {/* Steps timeline */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="space-y-0">
            {steps.map((step, index) => (
              <div key={index} className="flex gap-3">
                {/* Icon + connector */}
                <div className="flex flex-col items-center">
                  <StepIndicator status={step.status} index={index} />
                  {index < steps.length - 1 && (
                    <motion.div
                      className={cn(
                        "w-px flex-1 min-h-[32px]",
                        step.status === "completed" ? "bg-success" : "bg-border",
                      )}
                      initial={{ opacity: 0.5 }}
                      animate={{
                        opacity: step.status === "completed" ? 1 : 0.5,
                      }}
                      transition={{ duration: 0.3 }}
                    />
                  )}
                </div>

                {/* Step content */}
                <motion.div
                  className="pb-6 pt-1 min-w-0"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <p
                    className={cn(
                      "text-sm",
                      step.status === "active" && "font-medium text-text-primary",
                      step.status === "completed" && "text-text-secondary",
                      step.status === "pending" && "text-text-tertiary",
                      step.status === "failed" && "text-error font-medium",
                    )}
                  >
                    {step.name}
                  </p>
                  {step.detail && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="text-xs text-text-tertiary mt-0.5"
                    >
                      {step.detail}
                    </motion.p>
                  )}
                  {step.status === "active" && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: [0.4, 1, 0.4] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="flex items-center gap-1.5 mt-1"
                    >
                      <span className="inline-block h-1 w-1 rounded-full bg-primary" />
                      <span className="inline-block h-1 w-1 rounded-full bg-primary animation-delay-200" />
                      <span className="inline-block h-1 w-1 rounded-full bg-primary animation-delay-400" />
                    </motion.div>
                  )}
                  {step.status === "completed" && step.completed_at && step.started_at && (
                    <p className="text-[10px] text-text-tertiary mt-0.5">
                      {Math.round(
                        (new Date(step.completed_at).getTime() -
                          new Date(step.started_at).getTime()) /
                          1000,
                      )}
                      s
                    </p>
                  )}
                </motion.div>
              </div>
            ))}
          </div>
        </div>

        {/* Success footer */}
        <AnimatePresence>
          {showSuccess && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="px-6 py-4 border-t border-border"
            >
              <div className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] bg-success/10 border border-success/20">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 12, delay: 0.1 }}
                >
                  <SealCheck className="h-8 w-8 text-success" weight="fill" />
                </motion.div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    Enrichment Complete
                  </p>
                  <p className="text-xs text-text-secondary">
                    {fieldsPopulated
                      ? `${fieldsPopulated} fields populated`
                      : "Company profile updated"}
                    . Refreshing data...
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Failed footer */}
        <AnimatePresence>
          {taskStatus === "failed" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="px-6 py-4 border-t border-border"
            >
              <div className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] bg-error/10 border border-error/20">
                <Warning className="h-6 w-6 text-error" weight="fill" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-text-primary">Enrichment Failed</p>
                  <p className="text-xs text-text-secondary">
                    Something went wrong. No credits were consumed.
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 rounded-[var(--radius-sm)] hover:bg-primary/20 transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </AnimatePresence>
  );
}
