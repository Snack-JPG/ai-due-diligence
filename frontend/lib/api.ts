import {
  AnalysisDetail,
  AnalysisListResponse,
  ChatResponse,
  ReportResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function createAnalysis(payload: {
  name: string;
  company_name?: string;
  industry?: string;
  region?: string;
  focus_areas: string[];
  files: File[];
}) {
  const formData = new FormData();
  formData.append("name", payload.name);
  if (payload.company_name) formData.append("company_name", payload.company_name);
  if (payload.industry) formData.append("industry", payload.industry);
  if (payload.region) formData.append("region", payload.region);
  formData.append("focus_areas", JSON.stringify(payload.focus_areas));
  payload.files.forEach((file) => formData.append("files", file));
  return request<{ id: string; status: string; created_at: string }>("/api/analyses", {
    method: "POST",
    body: formData,
  });
}

export const getAnalysis = (id: string) => request<AnalysisDetail>(`/api/analyses/${id}`);
export const getAnalyses = (query = "") => request<AnalysisListResponse>(`/api/analyses${query}`);
export const getReport = (id: string) => request<ReportResponse>(`/api/analyses/${id}/report`);

export const submitCheckpoint = (id: string, body: Record<string, unknown>) =>
  request<{ status: string }>(`/api/analyses/${id}/checkpoint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const sendChat = (id: string, message: string) =>
  request<ChatResponse>(`/api/analyses/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, include_citations: true }),
  });

export function eventStreamUrl(id: string, lastEventId = 0) {
  return `${API_BASE}/api/analyses/${id}/events?last_event_id=${lastEventId}`;
}
