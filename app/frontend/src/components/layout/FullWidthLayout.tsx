"use client";

import { cn } from "@/lib/utils";

interface FullWidthLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function FullWidthLayout({ children, className }: FullWidthLayoutProps) {
  return (
    <div className={cn("max-w-[1280px] mx-auto w-full px-6 py-6", className)}>
      {children}
    </div>
  );
}
