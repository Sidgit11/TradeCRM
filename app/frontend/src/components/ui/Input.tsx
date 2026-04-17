"use client";

import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { MagnifyingGlass } from "@phosphor-icons/react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  inputSize?: "sm" | "md";
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  helperText?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, helperText, error, type, inputSize = "md", ...props }, ref) => {
    const isSearch = type === "search";
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-[13px] font-medium text-text-primary">{label}</label>
        )}
        <div className="relative">
          {isSearch && (
            <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
          )}
          <input
            ref={ref}
            type={type === "search" ? "text" : type}
            className={cn(
              "w-full rounded-[var(--radius-sm)] border border-border bg-surface px-3 text-sm text-text-primary placeholder:text-text-tertiary transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light disabled:opacity-50",
              inputSize === "sm" ? "h-8" : "h-9",
              isSearch && "pl-9",
              error && "border-error focus:ring-error/20 focus:border-error",
              className,
            )}
            {...props}
          />
        </div>
        {error && <p className="text-xs text-error">{error}</p>}
        {helperText && !error && (
          <p className="text-xs text-text-tertiary">{helperText}</p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, helperText, error, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-[13px] font-medium text-text-primary">{label}</label>
        )}
        <textarea
          ref={ref}
          className={cn(
            "w-full rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light disabled:opacity-50 resize-y min-h-[80px]",
            error && "border-error focus:ring-error/20 focus:border-error",
            className,
          )}
          {...props}
        />
        {error && <p className="text-xs text-error">{error}</p>}
        {helperText && !error && (
          <p className="text-xs text-text-tertiary">{helperText}</p>
        )}
      </div>
    );
  },
);

Textarea.displayName = "Textarea";
