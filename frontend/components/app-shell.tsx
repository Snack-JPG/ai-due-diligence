import Link from "next/link";
import { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell min-h-screen">
      <header className="border-b border-white/5">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <Link href="/" className="text-xl font-semibold tracking-[0.18em] text-cyan-200">
              DILIGENCE/OS
            </Link>
            <p className="mt-1 text-sm text-slate-400">AI due diligence workflow with live agent orchestration</p>
          </div>
          <nav className="flex items-center gap-3">
            <Link href="/" className="text-sm text-slate-300 hover:text-white">
              Upload
            </Link>
            <Link href="/history" className="text-sm text-slate-300 hover:text-white">
              History
            </Link>
            <Badge tone="success">Phase 1</Badge>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
    </div>
  );
}
