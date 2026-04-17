"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

type ModalSize = "sm" | "md" | "lg" | "full";

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  size?: ModalSize;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const sizeStyles: Record<ModalSize, string> = {
  sm: "max-w-[400px]",
  md: "max-w-[560px]",
  lg: "max-w-[720px]",
  full: "max-w-[90vw]",
};

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  size = "md",
  children,
  footer,
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full rounded-[var(--radius-lg)] bg-surface shadow-[var(--shadow-xl)] focus:outline-none",
            sizeStyles[size],
          )}
        >
          {title && (
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div>
                <Dialog.Title className="text-lg font-semibold font-[family-name:var(--font-heading)] text-text-primary">
                  {title}
                </Dialog.Title>
                {description && (
                  <Dialog.Description className="text-sm text-text-secondary mt-1">
                    {description}
                  </Dialog.Description>
                )}
              </div>
              <Dialog.Close className="rounded-[var(--radius-sm)] p-1 text-text-tertiary hover:text-text-primary hover:bg-border-light transition-colors">
                <X className="h-5 w-5" />
              </Dialog.Close>
            </div>
          )}
          <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">{children}</div>
          {footer && (
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border">
              {footer}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
