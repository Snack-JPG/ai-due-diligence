import "./globals.css";

import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
