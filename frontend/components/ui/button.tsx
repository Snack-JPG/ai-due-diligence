import * as React from "react";

import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "danger";
}

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "default" && "bg-primary text-slate-950 hover:bg-cyan-300",
        variant === "outline" && "border border-border bg-card/70 hover:bg-card",
        variant === "ghost" && "hover:bg-muted",
        variant === "danger" && "bg-danger text-white hover:bg-red-500",
        className,
      )}
      {...props}
    />
  );
}
