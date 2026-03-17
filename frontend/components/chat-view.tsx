"use client";

import { useState } from "react";

import { sendChat } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function ChatView({ analysisId }: { analysisId: string }) {
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string; citations?: Array<{ filename: string; locator: string }> }>>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSend() {
    if (!draft.trim()) return;
    const question = draft;
    setDraft("");
    setMessages((current) => [...current, { role: "user", content: question }]);
    setLoading(true);
    try {
      const response = await sendChat(analysisId, question);
      setMessages((current) => [...current, { role: "assistant", content: response.answer, citations: response.citations }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <CardHeader>
          <CardTitle>Chat View</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="min-h-[460px] space-y-4 rounded-2xl border border-border bg-slate-950/30 p-4">
            {messages.length === 0 ? <p className="text-sm text-slate-500">Ask follow-up questions about the analysis.</p> : null}
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                  message.role === "user" ? "ml-auto bg-cyan-500/15 text-cyan-100" : "bg-white/5 text-slate-100"
                }`}
              >
                <p>{message.content}</p>
                {message.citations?.length ? (
                  <div className="mt-3 space-y-1 text-xs text-slate-400">
                    {message.citations.map((citation) => (
                      <div key={`${citation.filename}-${citation.locator}`}>
                        {citation.filename} · {citation.locator}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <Input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="What are the biggest legal risks?" />
            <Button onClick={onSend} disabled={loading}>
              {loading ? "Asking..." : "Send"}
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Suggested prompts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            "What contradictions matter most before investment?",
            "Which missing documents create the largest confidence gap?",
            "Summarize the strongest market risks with citations.",
            "What should I ask management next?",
          ].map((prompt) => (
            <button
              key={prompt}
              className="w-full rounded-xl border border-border bg-slate-950/30 p-4 text-left text-sm text-slate-300 hover:bg-slate-900"
              onClick={() => setDraft(prompt)}
            >
              {prompt}
            </button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
