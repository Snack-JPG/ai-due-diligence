export type AgentStatus = "pending" | "running" | "completed" | "failed" | "skipped";
export type AnalysisStatus =
  | "created"
  | "processing_documents"
  | "running_agents"
  | "awaiting_checkpoint"
  | "synthesizing"
  | "completed"
  | "failed";
export type CheckpointStatus = "pending" | "approved" | "rejected" | "deepen_requested" | "not_required";

export interface Citation {
  document_id?: string | null;
  filename: string;
  locator: string;
  quote?: string | null;
  source_type: "upload" | "web" | "report" | "agent_output";
  url?: string | null;
}

export interface RiskFlag {
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  citations: Citation[];
}

export interface AgentEnvelope {
  agent_name: "financial" | "legal" | "market" | "synthesiser";
  status: AgentStatus;
  started_at?: string | null;
  completed_at?: string | null;
  trace_id?: string | null;
  error_message?: string | null;
  payload?: Record<string, unknown> | null;
}

export interface ProgressEvent {
  id?: number;
  type: string;
  analysis_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface AnalysisDetail {
  id: string;
  name: string;
  status: AnalysisStatus;
  checkpoint_status: CheckpointStatus;
  company_name?: string | null;
  industry?: string | null;
  region?: string | null;
  focus_areas: string[];
  created_at: string;
  updated_at: string;
  documents: Array<Record<string, unknown>>;
  agents: Record<string, AgentEnvelope>;
  report_available: boolean;
  events: ProgressEvent[];
  error_message?: string | null;
}

export interface ReportSection {
  summary: string;
  key_findings: string[];
  flags: RiskFlag[];
}

export interface DueDiligenceReport {
  executive_summary: string;
  financial: ReportSection;
  legal: ReportSection;
  market: ReportSection;
  contradictions: Array<{ topic: string; description: string; agents_involved: string[]; citations: Citation[] }>;
  overall_risk: number;
  recommendations: Array<{ action: string; priority: "low" | "medium" | "high"; rationale: string }>;
  generated_at: string;
}

export interface ReportResponse {
  analysis_id: string;
  markdown: string;
  summary: DueDiligenceReport;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  trace_id?: string | null;
}

export interface AnalysisListResponse {
  items: Array<{
    id: string;
    name: string;
    status: AnalysisStatus;
    checkpoint_status: CheckpointStatus;
    company_name?: string | null;
    created_at: string;
    updated_at: string;
  }>;
  total: number;
  page: number;
  page_size: number;
}
