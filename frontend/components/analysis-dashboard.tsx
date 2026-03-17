"use client";

import Link from "next/link";
import { useState } from "react";

import { submitCheckpoint } from "@/lib/api";
import { useAnalysisStream } from "@/hooks/use-analysis-stream";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { formatDate } from "@/lib/utils";

const AGENTS = ["financial", "legal", "market", "synthesiser"] as const;

function toneForStatus(status?: string) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "warning";
  return "neutral";
}

export function AnalysisDashboard({ analysisId }: { analysisId: string }) {
  const { analysis, events, error } = useAnalysisStream(analysisId);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  if (!analysis) {
    return <div className="text-sm text-slate-400">Loading analysis...</div>;
  }

  const completedCount = AGENTS.filter((agent) => analysis.agents[agent]?.status === "completed").length;
  const progress = (completedCount / AGENTS.length) * 100;

  async function sendDecision(decision: "approve" | "reject" | "deepen", focus_agents: string[] = []) {
    setBusy(true);
    try {
      await submitCheckpoint(analysisId, {
        decision,
        reason,
        focus_agents,
        requested_at: new Date().toISOString(),
      });
      setReason("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.6fr]">
        <Card>
          <CardHeader>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/70">Analysis View</p>
              <CardTitle className="mt-2 text-3xl">{analysis.name}</CardTitle>
              <p className="mt-2 text-sm text-slate-400">
                Status: {analysis.status} · Checkpoint: {analysis.checkpoint_status}
              </p>
            </div>
            <div className="w-64">
              <Progress value={progress} />
              <p className="mt-2 text-xs text-slate-500">{completedCount} of 4 agents completed</p>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {AGENTS.map((agent) => (
              <Card key={agent} className="border-white/5 bg-slate-950/35">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base capitalize">{agent}</CardTitle>
                  <Badge tone={toneForStatus(analysis.agents[agent]?.status)}>{analysis.agents[agent]?.status ?? "pending"}</Badge>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-slate-400">
                  <p>{String((analysis.agents[agent]?.payload as { summary?: string } | undefined)?.summary ?? "Awaiting execution.")}</p>
                  {analysis.agents[agent]?.error_message ? (
                    <p className="text-red-300">{analysis.agents[agent]?.error_message}</p>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Run actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {analysis.report_available ? (
              <>
                <Link href={`/analyses/${analysisId}/report`} className="block">
                  <Button className="w-full">Open report</Button>
                </Link>
                <Link href={`/analyses/${analysisId}/chat`} className="block">
                  <Button variant="outline" className="w-full">
                    Open chat
                  </Button>
                </Link>
              </>
            ) : null}
            {analysis.status === "awaiting_checkpoint" ? (
              <>
                <Input placeholder="Checkpoint reason or deeper-analysis focus" value={reason} onChange={(event) => setReason(event.target.value)} />
                <Button className="w-full" disabled={busy} onClick={() => sendDecision("approve")}>
                  Approve synthesis
                </Button>
                <Button className="w-full" variant="outline" disabled={busy} onClick={() => sendDecision("deepen", ["financial", "legal", "market"])}>
                  Request deeper analysis
                </Button>
                <Button className="w-full" variant="danger" disabled={busy} onClick={() => sendDecision("reject")}>
                  Reject run
                </Button>
              </>
            ) : (
              <p className="text-sm text-slate-400">Checkpoint actions appear here when the initial branches finish.</p>
            )}
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Documents</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {analysis.documents.map((document) => (
              <div key={String(document.id)} className="rounded-xl border border-border bg-slate-950/30 p-4">
                <div className="text-sm font-medium">{String(document.filename)}</div>
                <div className="mt-1 text-xs text-slate-500">{String(document.parse_status)}</div>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Live event feed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            {events.length === 0 ? (
              <div className="text-sm text-slate-500">No events yet.</div>
            ) : (
              events
                .slice()
                .reverse()
                .map((event) => (
                  <div key={`${event.id}-${event.timestamp}`} className="rounded-xl border border-border bg-slate-950/30 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium">{event.type}</div>
                      <div className="text-xs text-slate-500">{formatDate(event.timestamp)}</div>
                    </div>
                    <pre className="mt-3 overflow-auto text-xs text-slate-400">{JSON.stringify(event.payload, null, 2)}</pre>
                  </div>
                ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
