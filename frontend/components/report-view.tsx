"use client";

import { useEffect, useState } from "react";

import { getReport } from "@/lib/api";
import { ReportResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function scoreTone(score: number) {
  if (score >= 8) return "danger";
  if (score >= 5) return "warning";
  return "success";
}

export function ReportView({ analysisId }: { analysisId: string }) {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReport(analysisId).then(setReport).catch((loadError) => setError((loadError as Error).message));
  }, [analysisId]);

  if (error) return <div className="text-sm text-red-300">{error}</div>;
  if (!report) return <div className="text-sm text-slate-400">Loading report...</div>;

  const summary = report.summary;
  const sections = [
    { title: "Financial", section: summary.financial },
    { title: "Legal", section: summary.legal },
    { title: "Market", section: summary.market },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/70">Report View</p>
            <CardTitle className="mt-2 text-3xl">Due diligence report</CardTitle>
          </div>
          <div className="flex items-center gap-3">
            <Badge tone={scoreTone(summary.overall_risk)}>Overall risk {summary.overall_risk}/10</Badge>
            <Button variant="outline" onClick={() => window.print()}>
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="max-w-4xl text-lg leading-8 text-slate-200">{summary.executive_summary}</p>
        </CardContent>
      </Card>
      <div className="grid gap-6 lg:grid-cols-3">
        {sections.map(({ title, section }) => (
          <Card key={title}>
            <CardHeader>
              <CardTitle>{title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-7 text-slate-300">{section.summary}</p>
              <div className="space-y-2">
                {section.key_findings.map((finding) => (
                  <div key={finding} className="rounded-xl border border-border bg-slate-950/30 p-3 text-sm">
                    {finding}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[0.7fr_1.3fr]">
        <Card>
          <CardHeader>
            <CardTitle>Contradictions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary.contradictions.length === 0 ? (
              <p className="text-sm text-slate-500">No contradictions surfaced.</p>
            ) : (
              summary.contradictions.map((contradiction) => (
                <div key={contradiction.topic} className="rounded-xl border border-border bg-slate-950/30 p-4">
                  <div className="font-medium">{contradiction.topic}</div>
                  <p className="mt-2 text-sm text-slate-400">{contradiction.description}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recommendations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary.recommendations.map((recommendation) => (
              <div key={recommendation.action} className="rounded-xl border border-border bg-slate-950/30 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">{recommendation.action}</div>
                  <Badge tone={recommendation.priority === "high" ? "danger" : recommendation.priority === "medium" ? "warning" : "success"}>
                    {recommendation.priority}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-slate-400">{recommendation.rationale}</p>
              </div>
            ))}
            <details className="rounded-xl border border-border bg-slate-950/30 p-4">
              <summary className="cursor-pointer text-sm font-medium text-slate-200">Raw markdown report</summary>
              <pre className="mt-4 whitespace-pre-wrap text-xs text-slate-400">{report.markdown}</pre>
            </details>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
