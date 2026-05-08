import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/utils/cn";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  icon?: LucideIcon;
  hint?: React.ReactNode;
  tone?: "neutral" | "primary" | "accent" | "success" | "warning" | "destructive";
  className?: string;
}

const TONE_CLASSES: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "text-foreground",
  primary: "text-primary",
  accent: "text-accent",
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
};

const TONE_BG: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "bg-muted text-muted-foreground",
  primary: "bg-primary/10 text-primary",
  accent: "bg-accent-muted text-accent",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  destructive: "bg-destructive/10 text-destructive",
};

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  tone = "neutral",
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card shadow-card p-5 flex flex-col gap-3",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        {Icon && (
          <span
            className={cn(
              "inline-flex h-8 w-8 items-center justify-center rounded-lg",
              TONE_BG[tone],
            )}
          >
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <div className={cn("text-3xl font-semibold tracking-tight", TONE_CLASSES[tone])}>
        {value}
      </div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
