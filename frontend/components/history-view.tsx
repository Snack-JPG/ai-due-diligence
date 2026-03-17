"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getAnalyses } from "@/lib/api";
import { AnalysisListResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatDate } from "@/lib/utils";

function tone(status: string) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "awaiting_checkpoint") return "warning";
  return "neutral";
}

export function HistoryView() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<AnalysisListResponse | null>(null);

  useEffect(() => {
    getAnalyses(query ? `?q=${encodeURIComponent(query)}` : "").then(setData);
  }, [query]);

  return (
    <Card>
      <CardHeader>
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/70">History View</p>
          <CardTitle className="mt-2 text-3xl">Past analyses</CardTitle>
        </div>
        <div className="w-80">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search analyses" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {data?.items.length ? (
          data.items.map((item) => (
            <Link key={item.id} href={`/analyses/${item.id}`} className="block rounded-2xl border border-border bg-slate-950/30 p-4 transition hover:bg-slate-900/80">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-medium text-slate-100">{item.name}</div>
                  <div className="mt-1 text-sm text-slate-500">{item.company_name ?? "No company name"} · {formatDate(item.updated_at)}</div>
                </div>
                <Badge tone={tone(item.status)}>{item.status}</Badge>
              </div>
            </Link>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-slate-500">
            No analyses found.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
