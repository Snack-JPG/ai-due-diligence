# AI Due Diligence Agent Technical Specification

## 1. Purpose

The AI Due Diligence Agent is a production-grade web application for automated business due diligence. Users upload company materials such as financial statements, contracts, investor decks, board materials, reports, and operating spreadsheets. A LangGraph-based orchestrator processes the corpus, routes the analysis to specialized agents, pauses for human review after the initial pass, and then synthesizes the results into a structured due diligence report with supporting evidence and follow-up chat.

The system is designed as a portfolio project, but the implementation standard is production-oriented:

- deterministic workflow orchestration
- typed agent outputs
- traceability from finding to source chunk
- auditable human approval checkpoint
- observable execution via LangSmith
- frontend streaming for real-time progress
- modular LLM provider abstraction

## 2. Product Goals

### Primary goals

- Reduce time required to perform initial business due diligence on a target company.
- Demonstrate a robust multi-agent architecture using LangGraph.
- Produce defensible, evidence-backed outputs instead of free-form summaries.
- Support iterative analyst workflows through checkpointing and follow-up chat.

### Non-goals for Phase 1

- OCR for scanned documents with poor text quality
- multi-tenant enterprise authorization
- external CRM or data room integrations
- automated legal advice or final investment recommendation
- advanced spreadsheet modeling or ratio forecasting beyond extracted metrics

## 3. Users and Core Jobs

### Primary users

- investors
- analysts
- founders preparing for diligence
- consultants

### Core jobs

- upload a set of company documents
- launch an analysis run with a title and optional context
- monitor agent progress in real time
- review intermediate findings before synthesis
- read the final report and export it
- ask follow-up questions grounded in uploaded documents and generated findings
- retrieve prior analyses

## 4. Functional Requirements

### 4.1 Analysis lifecycle

1. User creates a new analysis and uploads one or more documents.
2. Backend stores metadata in SQLite and files on local disk.
3. Document processing pipeline extracts text, chunks content, embeds chunks, and stores them in a ChromaDB collection scoped to the analysis.
4. LangGraph execution begins.
5. Financial Analyst, Legal Analyst, and Market Research agents run in parallel.
6. Their structured outputs are persisted and streamed to the frontend as partial updates.
7. Workflow enters a human-in-the-loop checkpoint.
8. User approves, rejects, or requests deeper analysis.
9. If approved, Synthesiser Agent combines outputs into the final report.
10. Final markdown report and structured JSON summary are stored.
11. User can chat with the system about the report and source documents.

### 4.2 Required behaviors

- Support multiple document types in a single analysis.
- Preserve citation metadata for each extracted finding.
- Allow partial failure handling per agent without crashing the entire workflow.
- Persist workflow state so the user can refresh or revisit progress.
- Stream status transitions and findings to the frontend over SSE.
- Expose a stable JSON contract for frontend rendering.
- Maintain an audit trail for checkpoint decisions and prompts used.

## 5. System Scope

### Inputs

- uploaded files: PDF, DOCX, XLSX, CSV, TXT
- analysis name
- optional analysis context:
  - target company name
  - industry
  - geography
  - diligence focus

### Outputs

- per-agent structured JSON outputs
- final markdown due diligence report
- final structured JSON summary
- chat responses with citations
- progress events and checkpoint status

## 6. High-Level Architecture

### Major components

- Next.js frontend
- FastAPI backend
- LangGraph orchestration layer
- LangChain tool and retrieval layer
- ChromaDB vector store
- SQLite metadata store
- local file storage for uploaded documents and derived artifacts
- LangSmith tracing and run observability

### Execution model

- request-response for CRUD APIs
- asynchronous background execution for document processing and analysis
- server-sent events for live progress updates
- persisted checkpoints for resumable workflows

## 7. Technology Stack

- Backend: Python 3.12
- API: FastAPI
- Agent framework: LangChain, LangGraph, LangSmith
- LLM default: OpenAI GPT-4o
- Embeddings: OpenAI `text-embedding-3-small`
- Vector store: ChromaDB local persistence
- Metadata DB: SQLite
- Document loaders: LangChain loaders plus file-type-specific parsers
- Frontend: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui
- Streaming: SSE from FastAPI
- Validation: Pydantic v2
- Testing: pytest, httpx, Playwright

## 8. Data Model

### 8.1 Core entities

#### Analysis

- `id`: UUID
- `name`: string
- `status`: enum
- `company_name`: optional string
- `industry`: optional string
- `region`: optional string
- `focus_areas`: JSON array of strings
- `created_at`: datetime
- `updated_at`: datetime
- `checkpoint_status`: enum
- `report_markdown`: nullable text
- `report_summary_json`: nullable JSON
- `error_message`: nullable text

#### Document

- `id`: UUID
- `analysis_id`: UUID
- `filename`: string
- `content_type`: string
- `size_bytes`: integer
- `storage_path`: string
- `parse_status`: enum
- `page_count`: nullable integer
- `created_at`: datetime

#### AgentRun

- `id`: UUID
- `analysis_id`: UUID
- `agent_name`: enum
- `status`: enum
- `started_at`: nullable datetime
- `completed_at`: nullable datetime
- `raw_output_json`: nullable JSON
- `error_message`: nullable text
- `trace_id`: nullable string

#### CheckpointDecision

- `id`: UUID
- `analysis_id`: UUID
- `decision`: enum `approve | reject | deepen`
- `reason`: nullable text
- `requested_focus`: nullable JSON
- `created_at`: datetime

#### ChatMessage

- `id`: UUID
- `analysis_id`: UUID
- `role`: enum `user | assistant | system`
- `content`: text
- `citations_json`: nullable JSON
- `created_at`: datetime

### 8.2 Status enums

#### AnalysisStatus

- `created`
- `processing_documents`
- `running_agents`
- `awaiting_checkpoint`
- `synthesizing`
- `completed`
- `failed`

#### AgentStatus

- `pending`
- `running`
- `completed`
- `failed`
- `skipped`

## 9. Document Processing Pipeline

### 9.1 Upload and storage

- Files are uploaded with multipart form data.
- Backend generates a stable analysis ID and stores files under `data/uploads/{analysis_id}/`.
- Original filenames are preserved in metadata but storage names should be normalized to avoid path issues.
- File size limits should be enforced server-side. Recommended Phase 1 defaults:
  - max file size: 50 MB per file
  - max files per analysis: 25
  - max combined size: 250 MB

### 9.2 Parsing

Use file-type-specific loaders:

- PDF: PyPDF-based loader
- DOCX: python-docx or Unstructured fallback
- XLSX: openpyxl-driven sheet extraction
- CSV: pandas or Python CSV reader
- TXT: plain text loader

The parser must capture:

- extracted text
- document-level metadata
- page numbers where available
- sheet names and row references for spreadsheets

### 9.3 Chunking

- splitter: `RecursiveCharacterTextSplitter`
- chunk size: 1000 characters
- chunk overlap: 200 characters
- attach metadata to each chunk:
  - analysis ID
  - document ID
  - filename
  - page number or sheet reference
  - chunk index
  - inferred document type

### 9.4 Embedding and storage

- embed with `text-embedding-3-small`
- store in ChromaDB collection named `analysis_{analysis_id}`
- persist collection to local disk
- include source metadata for later citation rendering

### 9.5 Retrieval strategy

Each agent queries the same collection with domain-specific prompts and filters.

- Financial agent favors financial statements, metrics tables, operating plans, cap tables, and investor updates.
- Legal agent favors contracts, policy documents, terms, disclosures, and regulatory language.
- Market agent uses uploaded materials plus external web search results and news summaries.

## 10. LangGraph Workflow Specification

### 10.1 Graph nodes

- `ingest_documents`
- `prepare_retrievers`
- `financial_agent`
- `legal_agent`
- `market_agent`
- `checkpoint_router`
- `human_checkpoint`
- `deeper_analysis_router`
- `synthesiser_agent`
- `chat_agent`
- `finalize_analysis`

### 10.2 Graph state

The shared graph state should be a typed Pydantic model or `TypedDict` with these fields:

- `analysis_id`: str
- `analysis_context`: dict
- `documents`: list of document metadata
- `financial_output`: optional structured object
- `legal_output`: optional structured object
- `market_output`: optional structured object
- `checkpoint_decision`: optional structured object
- `report_output`: optional structured object
- `chat_history`: list of messages
- `follow_up_question`: optional string
- `errors`: list of structured error objects
- `event_log`: list of progress events

### 10.3 Parallel routing

After retrieval resources are prepared, the graph fans out into three branches:

- financial analysis
- legal analysis
- market analysis

The graph waits for all three branches to resolve before entering the checkpoint node. If one branch fails, the graph continues with partial results and records the failure in state. The synthesizer must explicitly mention incomplete branches in the final output.

### 10.4 Human-in-the-loop behavior

After initial analysis:

- graph pauses with checkpoint status `awaiting_checkpoint`
- frontend displays summary cards for each agent
- user can:
  - approve synthesis
  - reject and stop the run
  - request deeper analysis with a text instruction

If the user requests deeper analysis:

- route back to one or more agent nodes
- include the user’s focus instruction in the agent prompt
- limit deepening to a configurable retry count, recommended default `2`

### 10.5 Synthesis

The synthesizer runs only after:

- all initial branches have completed or failed
- checkpoint decision is `approve`

It consumes all agent outputs, contradiction markers, and source citations, then emits:

- markdown report
- structured summary JSON
- category risk scores
- overall risk score

### 10.6 Conversational follow-up

Follow-up chat is a separate LangGraph or LangChain runnable that uses:

- report summary
- uploaded document retrieval
- prior chat history
- optional agent outputs as context blocks

Responses must remain grounded in sources and cite relevant chunks or findings.

## 11. Agent Specifications

### 11.1 Financial Analyst Agent

#### Responsibilities

- extract revenue, margins, burn rate, runway, growth rate, and unit economics
- identify anomalies and inconsistencies
- highlight missing financial data
- quantify confidence where evidence is incomplete

#### Inputs

- analysis context
- retrieved financial chunks
- calculator tool
- table parser tool

#### Outputs

- `FinancialMetrics`
- source citations
- risk flags

#### Failure policy

- if exact values are unavailable, return `null` for the metric with a missing-data flag
- do not fabricate values from implied context

### 11.2 Legal Analyst Agent

#### Responsibilities

- extract key contract and governance terms
- identify IP ownership issues
- identify liability, indemnity, and jurisdiction concerns
- summarize compliance risks

#### Inputs

- legal retrieval results
- keyword extraction tool

#### Outputs

- `LegalFindings`
- per-contract findings
- legal risk score

#### Failure policy

- record unavailable contract details explicitly
- downgrade confidence when documents appear incomplete

### 11.3 Market Research Agent

#### Responsibilities

- assess market size and trends
- identify competitors and positioning
- compare company claims against external evidence
- summarize recent relevant news

#### Inputs

- uploaded materials
- external web search results
- retrieved internal chunks

#### Outputs

- `MarketAnalysis`
- competitor list
- market/news risk indicators

#### Failure policy

- separate retrieved facts from model inference
- annotate freshness timestamp for web-derived evidence

### 11.4 Synthesiser Agent

#### Responsibilities

- combine all prior outputs into a coherent diligence report
- assign category risk scores on a 1 to 10 scale
- generate executive summary, detailed findings, contradictions, and recommendations

#### Inputs

- all agent outputs
- checkpoint decision context
- citations and event metadata

#### Outputs

- markdown report
- `DueDiligenceReport`
- contradiction list
- recommendations

## 12. Tools and Provider Abstractions

### Required tools

- `calculator_tool`
- `table_parser_tool`
- `rag_retrieval_tool`
- `keyword_extraction_tool`
- `web_search_tool`

### Tool design requirements

- tools must return structured outputs
- tools must include source metadata when applicable
- tool exceptions must be caught and surfaced as typed errors

### LLM abstraction

Wrap model initialization behind a provider factory:

- default provider: OpenAI GPT-4o
- alternate providers: Claude, Gemini, local-compatible models

The rest of the application should depend on a common chat model interface, not provider-specific logic.

## 13. API Specification

All endpoints are rooted at `/api`.

### 13.1 `POST /api/analyses`

Creates a new analysis and uploads documents.

#### Request

- multipart form data
- fields:
  - `name`: string, required
  - `company_name`: optional string
  - `industry`: optional string
  - `region`: optional string
  - `focus_areas`: optional JSON array
  - `files`: one or more uploaded files

#### Response

```json
{
  "id": "uuid",
  "status": "processing_documents",
  "created_at": "2026-03-17T11:00:00Z"
}
```

### 13.2 `GET /api/analyses/:id`

Returns analysis status and current structured results.

#### Response shape

```json
{
  "id": "uuid",
  "name": "Acme Seed Diligence",
  "status": "awaiting_checkpoint",
  "checkpoint_status": "pending",
  "documents": [],
  "agents": {
    "financial": {},
    "legal": {},
    "market": {}
  },
  "report_available": false,
  "events": []
}
```

### 13.3 `GET /api/analyses/:id/report`

Returns final markdown and structured report summary.

### 13.4 `POST /api/analyses/:id/chat`

Handles grounded follow-up questions.

#### Request

```json
{
  "message": "What are the biggest legal risks?",
  "include_citations": true
}
```

#### Response

```json
{
  "answer": "The most material legal risks are...",
  "citations": [],
  "trace_id": "langsmith-run-id"
}
```

### 13.5 `GET /api/analyses`

Lists prior analyses with pagination and search.

#### Query params

- `q`
- `status`
- `page`
- `page_size`

### 13.6 `POST /api/analyses/:id/checkpoint`

Submits the user’s checkpoint decision.

#### Request

```json
{
  "decision": "deepen",
  "reason": "Need more scrutiny on customer concentration and indemnity clauses.",
  "focus_agents": ["financial", "legal"]
}
```

## 14. Streaming and Frontend Event Contract

Use SSE endpoint:

- `GET /api/analyses/:id/events`

### Event types

- `analysis.created`
- `document.processing.started`
- `document.processing.completed`
- `agent.started`
- `agent.finding`
- `agent.completed`
- `agent.failed`
- `checkpoint.required`
- `checkpoint.received`
- `synthesiser.started`
- `report.completed`
- `analysis.failed`

### Example SSE payload

```json
{
  "type": "agent.finding",
  "analysis_id": "uuid",
  "timestamp": "2026-03-17T11:12:00Z",
  "payload": {
    "agent": "financial",
    "summary": "Runway estimated at 7.5 months based on cash balance and average burn.",
    "citations": [
      {
        "document_id": "uuid",
        "filename": "FY2025_PnL.xlsx",
        "locator": "Sheet: Summary, Row 18"
      }
    ]
  }
}
```

## 15. Frontend Specification

### 15.1 Upload View

Requirements:

- drag-and-drop zone
- file list with validation feedback
- analysis metadata form
- submit button disabled until valid input exists
- upload progress display

### 15.2 Analysis View

Requirements:

- live progress per agent
- timeline/event feed
- streaming findings cards
- checkpoint action panel
- clear incomplete/error states

### 15.3 Report View

Requirements:

- executive summary
- sectioned findings for financial, legal, and market
- risk score visualization
- contradictions section
- recommendations section
- citations
- export to PDF action

### 15.4 Chat View

Requirements:

- message history
- source-linked answers
- suggested follow-up prompts
- loading and streaming states

### 15.5 History View

Requirements:

- searchable analysis list
- status badges
- created date
- quick links to report or resume

## 16. Security and Compliance Considerations

Phase 1 is local-first, but the design should still apply basic security controls:

- validate MIME type and extension
- virus scanning hook point for uploaded files
- sanitize filenames
- limit upload sizes
- store secrets in environment variables only
- do not log raw confidential document contents
- redact PII in trace metadata where feasible
- add retention policy hooks for deleting uploads and embeddings

## 17. Reliability Requirements

- analysis runs must be resumable from persisted state
- background tasks must record terminal status on crash
- agent failures must not erase successful branch outputs
- checkpoint state must survive process restart
- SSE reconnect should allow client resume from last event ID

## 18. Observability

### LangSmith

- trace each analysis run with shared `analysis_id`
- include child spans for each tool call and agent node
- attach tags:
  - environment
  - agent_name
  - analysis_id
  - model_provider

### Application logging

- structured JSON logs
- request IDs and analysis IDs in all log lines
- log status transitions, tool failures, checkpoint actions, and API errors

### Metrics

- analysis duration
- document parsing duration
- embedding duration
- agent completion rate
- checkpoint approval rate
- chat latency

## 19. Testing Strategy

### Unit tests

- Pydantic schema validation
- parser normalization
- tool wrappers
- prompt rendering
- score calculation rules

### Integration tests

- end-to-end document upload flow
- graph execution with mocked LLM outputs
- checkpoint pause and resume
- report generation
- chat grounding behavior

### Frontend tests

- Upload View validation
- SSE event handling
- checkpoint interaction
- report rendering

### Evaluation tests

- golden datasets with expected findings
- hallucination checks for unsupported claims
- contradiction detection accuracy

## 20. Configuration

Recommended environment variables:

- `OPENAI_API_KEY`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- `MODEL_PROVIDER`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `CHROMA_PERSIST_DIR`
- `UPLOAD_DIR`
- `SQLITE_DATABASE_URL`
- `MAX_UPLOAD_MB`
- `MAX_FILES_PER_ANALYSIS`

## 21. Suggested Project Structure

```text
backend/
  app/
    api/
    core/
    db/
    graphs/
    agents/
    tools/
    schemas/
    services/
    repositories/
    streaming/
tests/
frontend/
  app/
  components/
  lib/
  hooks/
  types/
data/
  uploads/
  chroma/
```

## 22. Build Sequence Recommendation

1. Implement data models and storage layer.
2. Build upload and document ingestion pipeline.
3. Add ChromaDB indexing and retrieval.
4. Implement agent prompts and structured outputs.
5. Build LangGraph orchestration and checkpoint persistence.
6. Expose REST and SSE APIs.
7. Build frontend upload and analysis views.
8. Add report rendering and chat.
9. Add tracing, tests, and evaluation datasets.

## 23. Acceptance Criteria

- User can upload mixed-format documents and create an analysis.
- System indexes the uploaded content and runs three specialist agents in parallel.
- Each agent returns validated structured output with citations.
- Workflow pauses for human approval before synthesis.
- Synthesizer produces final markdown and structured JSON report.
- Frontend displays streaming status and findings in real time.
- User can ask follow-up questions grounded in report and source materials.
- Analysis history is queryable.
- Traces are available in LangSmith for the full run.

## 24. Risks and Known Tradeoffs

- local ChromaDB and SQLite are appropriate for Phase 1 but not high-concurrency production workloads
- spreadsheet extraction quality can vary substantially by layout
- web search introduces freshness and consistency issues relative to uploaded materials
- LLM-based extraction may miss subtle legal edge cases without domain tuning
- report quality depends heavily on document completeness

## 25. Phase 2 Extensions

- OCR and image-based document support
- user and organization auth
- multi-tenant storage
- exportable diligence data rooms
- benchmark datasets and scoring dashboards
- analyst feedback loops and prompt optimization
- Slack or email notifications
