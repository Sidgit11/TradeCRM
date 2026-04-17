"use client";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { AgentStatusBar } from "./AgentStatusBar";

interface AppShellProps {
  title: string;
  children: React.ReactNode;
}

export function AppShell({ title, children }: AppShellProps) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar title={title} />
        <main className="flex-1 overflow-y-auto pb-10">{children}</main>
        <AgentStatusBar />
      </div>
    </div>
  );
}
