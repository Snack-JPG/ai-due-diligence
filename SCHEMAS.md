# Structured Output Schemas

This document defines the Pydantic models for all structured outputs in Phase 1. The examples use Pydantic v2 style and are intended to be copied directly into `backend/app/schemas/`.

## Design Notes

- All numeric values that may be unavailable should be nullable.
- Every material finding should support citations.
- Risk scores use a `1` to `10` scale where `10` is highest risk.
- Confidence uses a constrained categorical enum to keep frontend rendering simple.

## Common Types

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Citation(BaseModel):
    document_id: str | None = Field(default=None)
    filename: str
    locator: str = Field(
        description="Page number, sheet/cell range, paragraph reference, or URL."
    )
    quote: str | None = Field(
        default=None,
        description="Short supporting excerpt where safe to store."
    )
    source_type: Literal["upload", "web", "report", "agent_output"] = "upload"
    url: str | None = None


class RiskFlag(BaseModel):
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    citations: list[Citation] = Field(default_factory=list)


class MetricValue(BaseModel):
    value: float | None = None
    unit: str | None = None
    period: str | None = Field(
        default=None,
        description="Examples: FY2025, Q4 2025, trailing twelve months."
    )
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    rationale: str | None = None
    citations: list[Citation] = Field(default_factory=list)
```

## Financial Models

```python
class UnitEconomics(BaseModel):
    cac: MetricValue | None = None
    ltv: MetricValue | None = None
    payback_period_months: MetricValue | None = None
    gross_margin_per_unit: MetricValue | None = None
    notes: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class FinancialMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revenue: MetricValue | None = None
    gross_margin: MetricValue | None = None
    net_margin: MetricValue | None = None
    burn_rate: MetricValue | None = None
    runway: MetricValue | None = None
    growth_rate: MetricValue | None = None
    unit_economics: UnitEconomics | None = None
    anomalies: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    flags: list[RiskFlag] = Field(default_factory=list)
    summary: str
```

## Legal Models

```python
class ContractFinding(BaseModel):
    name: str
    contract_type: str | None = None
    counterparty: str | None = None
    effective_date: str | None = None
    governing_law: str | None = None
    termination_terms: str | None = None
    liability_terms: str | None = None
    indemnity_terms: str | None = None
    exclusivity_terms: str | None = None
    unusual_terms: list[str] = Field(default_factory=list)
    missing_protections: list[str] = Field(default_factory=list)
    risk_score: int = Field(ge=1, le=10)
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    citations: list[Citation] = Field(default_factory=list)


class IPStatus(BaseModel):
    ownership_summary: str
    assignment_gaps: list[str] = Field(default_factory=list)
    trademark_notes: list[str] = Field(default_factory=list)
    patent_notes: list[str] = Field(default_factory=list)
    open_source_risks: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class LegalFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contracts: list[ContractFinding] = Field(default_factory=list)
    ip_status: IPStatus
    compliance_issues: list[str] = Field(default_factory=list)
    jurisdiction_risks: list[str] = Field(default_factory=list)
    flags: list[RiskFlag] = Field(default_factory=list)
    risk_score: int = Field(ge=1, le=10)
    summary: str
```

## Market Models

```python
class Competitor(BaseModel):
    name: str
    category: str | None = None
    relative_positioning: str | None = None
    threat_level: Literal["low", "medium", "high"] = "medium"
    citations: list[Citation] = Field(default_factory=list)


class NewsItem(BaseModel):
    title: str
    date: str | None = None
    source: str
    summary: str
    relevance: str
    url: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class MarketSize(BaseModel):
    tam: MetricValue | None = None
    sam: MetricValue | None = None
    som: MetricValue | None = None
    notes: str | None = None


class MarketAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_size: MarketSize | None = None
    competitors: list[Competitor] = Field(default_factory=list)
    positioning: str
    industry_trends: list[str] = Field(default_factory=list)
    claim_validation: list[str] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    flags: list[RiskFlag] = Field(default_factory=list)
    risk_score: int = Field(ge=1, le=10)
    summary: str
```

## Final Report Models

```python
class Recommendation(BaseModel):
    action: str
    priority: Literal["low", "medium", "high"]
    rationale: str


class Contradiction(BaseModel):
    topic: str
    description: str
    agents_involved: list[Literal["financial", "legal", "market"]]
    citations: list[Citation] = Field(default_factory=list)


class ReportSection(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    flags: list[RiskFlag] = Field(default_factory=list)


class DueDiligenceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    financial: ReportSection
    legal: ReportSection
    market: ReportSection
    contradictions: list[Contradiction] = Field(default_factory=list)
    overall_risk: int = Field(ge=1, le=10)
    recommendations: list[Recommendation] = Field(default_factory=list)
    generated_at: datetime
```

## Analysis and Workflow Models

```python
class AgentStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class AnalysisStatus(str, Enum):
    created = "created"
    processing_documents = "processing_documents"
    running_agents = "running_agents"
    awaiting_checkpoint = "awaiting_checkpoint"
    synthesizing = "synthesizing"
    completed = "completed"
    failed = "failed"


class AgentResultEnvelope(BaseModel):
    agent_name: Literal["financial", "legal", "market", "synthesiser"]
    status: AgentStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    trace_id: str | None = None
    error_message: str | None = None
    payload: FinancialMetrics | LegalFindings | MarketAnalysis | DueDiligenceReport | None = None


class CheckpointDecision(BaseModel):
    decision: Literal["approve", "reject", "deepen"]
    reason: str | None = None
    focus_agents: list[Literal["financial", "legal", "market"]] = Field(default_factory=list)
    requested_at: datetime


class ProgressEvent(BaseModel):
    type: str
    analysis_id: str
    timestamp: datetime
    payload: dict = Field(default_factory=dict)
```

## Chat Models

```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    include_citations: bool = True


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    trace_id: str | None = None
```

## Notes for Implementation

- Keep schema modules separated by domain to avoid large monolithic files.
- Use `extra="forbid"` on agent output models so malformed LLM responses fail fast.
- Validate agent responses immediately after generation and retry once with a schema-repair prompt if needed.
- Store citation metadata in a form directly renderable by the frontend to avoid adapter duplication.
