"use client";

import { cn } from "@/lib/utils";
import { useAgentStore } from "@/stores/agent-store";

export function AgentStatusBar() {
  const { currentTask, isPanelExpanded, togglePanel } = useAgentStore();
  const isWorking = currentTask && currentTask.status === "running";

  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 h-10 bg-surface border-t border-border flex items-center px-4 z-40 cursor-pointer",
      )}
      onClick={togglePanel}
    >
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "h-2 w-2 rounded-full",
            isWorking ? "bg-primary animate-pulse-dot" : "bg-success",
          )}
        />
        <span className="text-xs text-text-secondary">
          {isWorking
            ? `Working: ${currentTask.steps[currentTask.current_step_index]?.name || "Processing..."}`
            : "Agent ready"}
        </span>
      </div>
    </div>
  );
}
