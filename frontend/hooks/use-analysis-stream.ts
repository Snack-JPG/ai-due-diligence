"use client";

import { useEffect, useState } from "react";

import { eventStreamUrl, getAnalysis } from "@/lib/api";
import { AnalysisDetail, ProgressEvent } from "@/lib/types";

export function useAnalysisStream(analysisId: string) {
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let source: EventSource | null = null;
    let lastEventId = 0;
    getAnalysis(analysisId)
      .then((payload) => {
        setAnalysis(payload);
        setEvents(payload.events);
        lastEventId = payload.events[payload.events.length - 1]?.id ?? 0;
        source = new EventSource(eventStreamUrl(analysisId, lastEventId));
        source.onmessage = () => {};
        source.addEventListener("analysis.created", async () => {
          setAnalysis(await getAnalysis(analysisId));
        });
        const handler = async (event: MessageEvent<string>) => {
          const parsed = JSON.parse(event.data) as ProgressEvent;
          setEvents((current) => [...current, parsed]);
          setAnalysis(await getAnalysis(analysisId));
        };
        [
          "document.processing.started",
          "document.processing.completed",
          "agent.started",
          "agent.finding",
          "agent.completed",
          "agent.failed",
          "checkpoint.required",
          "checkpoint.received",
          "synthesiser.started",
          "report.completed",
          "analysis.failed",
        ].forEach((type) => source?.addEventListener(type, handler));
        source.onerror = () => setError("Live stream disconnected. Refresh to resync.");
      })
      .catch((streamError) => setError((streamError as Error).message));
    return () => {
      source?.close();
    };
  }, [analysisId]);

  return { analysis, events, error, refresh: () => getAnalysis(analysisId).then(setAnalysis) };
}
