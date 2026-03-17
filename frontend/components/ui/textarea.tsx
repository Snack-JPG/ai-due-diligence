import * as React from "react";

import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn("min-h-28 w-full rounded-xl border border-border bg-slate-950/40 px-4 py-3 text-sm outline-none placeholder:text-slate-500 focus:border-cyan-500", className)}
      {...props}
    />
  );
}
