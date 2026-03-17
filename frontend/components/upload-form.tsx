"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createAnalysis } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function UploadForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");
  const [region, setRegion] = useState("");
  const [focusAreas, setFocusAreas] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valid = name.trim().length > 0 && files.length > 0;

  async function onSubmit() {
    try {
      setSubmitting(true);
      setError(null);
      const result = await createAnalysis({
        name,
        company_name: companyName,
        industry,
        region,
        focus_areas: focusAreas
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        files,
      });
      router.push(`/analyses/${result.id}`);
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <Card className="overflow-hidden">
        <CardHeader>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/70">Upload View</p>
            <CardTitle className="mt-2 text-3xl">Launch a diligence run</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <label className="block rounded-2xl border border-dashed border-cyan-500/40 bg-cyan-500/5 p-8 text-center">
            <div className="text-sm text-slate-300">Drag documents here or browse</div>
            <div className="mt-2 text-xs text-slate-500">PDF, DOCX, XLSX, CSV, TXT</div>
            <input
              type="file"
              multiple
              className="hidden"
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            />
          </label>
          <div className="space-y-3">
            {files.length === 0 ? (
              <div className="rounded-xl border border-border bg-slate-950/30 p-4 text-sm text-slate-500">
                No files selected yet.
              </div>
            ) : (
              files.map((file) => (
                <div key={`${file.name}-${file.size}`} className="rounded-xl border border-border bg-slate-950/30 p-4 text-sm">
                  <div className="font-medium text-slate-100">{file.name}</div>
                  <div className="text-slate-500">{Math.round(file.size / 1024)} KB</div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Analysis metadata</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input placeholder="Analysis name" value={name} onChange={(event) => setName(event.target.value)} />
          <Input placeholder="Company name" value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
          <Input placeholder="Industry" value={industry} onChange={(event) => setIndustry(event.target.value)} />
          <Input placeholder="Region" value={region} onChange={(event) => setRegion(event.target.value)} />
          <Textarea
            placeholder="Focus areas, comma-separated"
            value={focusAreas}
            onChange={(event) => setFocusAreas(event.target.value)}
          />
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          <Button className="w-full" disabled={!valid || submitting} onClick={onSubmit}>
            {submitting ? "Starting analysis..." : "Start analysis"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
