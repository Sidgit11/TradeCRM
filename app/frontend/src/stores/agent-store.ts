import { create } from "zustand";
import type { AgentTask } from "@/types";

interface AgentState {
  activeTasks: AgentTask[];
  currentTask: AgentTask | null;
  isPanelExpanded: boolean;
  setCurrentTask: (task: AgentTask | null) => void;
  updateTask: (task: AgentTask) => void;
  removeTask: (taskId: string) => void;
  togglePanel: () => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  activeTasks: [],
  currentTask: null,
  isPanelExpanded: false,
  setCurrentTask: (task) => set({ currentTask: task }),
  updateTask: (task) =>
    set((state) => {
      const existing = state.activeTasks.findIndex((t) => t.id === task.id);
      const tasks = [...state.activeTasks];
      if (existing >= 0) {
        tasks[existing] = task;
      } else {
        tasks.push(task);
      }
      return {
        activeTasks: tasks,
        currentTask: state.currentTask?.id === task.id ? task : state.currentTask,
      };
    }),
  removeTask: (taskId) =>
    set((state) => ({
      activeTasks: state.activeTasks.filter((t) => t.id !== taskId),
      currentTask: state.currentTask?.id === taskId ? null : state.currentTask,
    })),
  togglePanel: () => set((state) => ({ isPanelExpanded: !state.isPanelExpanded })),
}));
