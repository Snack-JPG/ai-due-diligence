import * as React from "react";

import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { tone?: "neutral" | "success" | "warning" | "danger" }) {
  return (
    <div
      className={cn(
        "inline-flex rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-[0.16em]",
        tone === "neutral" && "border-border bg-muted/60 text-slate-300",
        tone === "success" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
        tone === "warning" && "border-amber-500/30 bg-amber-500/10 text-amber-300",
        tone === "danger" && "border-red-500/30 bg-red-500/10 text-red-300",
        className,
      )}
      {...props}
    />
  );
}
