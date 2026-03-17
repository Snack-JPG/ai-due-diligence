import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn("w-full rounded-xl border border-border bg-slate-950/40 px-4 py-3 text-sm outline-none ring-0 placeholder:text-slate-500 focus:border-cyan-500", className)}
      {...props}
    />
  );
}
