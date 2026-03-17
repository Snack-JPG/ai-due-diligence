# AI Due Diligence Agent Architecture

## Overview

The system is a document-centric, multi-agent workflow built around LangGraph orchestration. Uploaded company materials are parsed, embedded, and stored once. Three specialist agents query the same analysis-scoped knowledge base in parallel, then a synthesizer creates the final report after a human checkpoint.

## Architecture Diagram

```text
                         +-----------------------------+
                         |         Next.js App         |
                         |-----------------------------|
                         | Upload | Analysis | Report  |
                         | Chat   | History  | SSE UI  |
                         +-------------+---------------+
                                       |
                             HTTPS / JSON / SSE
                                       |
                        +--------------v---------------+
                        |         FastAPI Backend      |
                        |------------------------------|
                        | REST API | SSE | Auth Hooks  |
                        +------+-----------+-----------+
                               |           |
                               |           +----------------------+
                               |                                  |
                    +----------v-----------+            +---------v---------+
                    |   Metadata Service   |            |  File Storage     |
                    |----------------------|            |-------------------|
                    | SQLite               |            | data/uploads/...  |
                    | analyses             |            | original files    |
                    | documents            |            | derived artifacts |
                    | agent_runs           |            +-------------------+
                    | chat_messages        |
                    | checkpoints          |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |  Document Pipeline   |
                    |----------------------|
                    | loaders/parsers      |
                    | chunking             |
                    | embeddings           |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |      ChromaDB        |
                    |----------------------|
                    | collection per run   |
                    | chunk metadata       |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |   LangGraph Engine   |
                    |----------------------|
                    | StateGraph           |
                    | conditional edges    |
                    | checkpoint interrupt |
                    +----+---------+-------+
                         |         |
             +-----------+         +---------------------------+
             |                                               |
   +---------v---------+   +---------v---------+   +---------v---------+
   | Financial Agent   |   | Legal Agent       |   | Market Agent      |
   |-------------------|   |-------------------|   |-------------------|
   | calculator        |   | keyword extract   |   | web search        |
   | table parser      |   | RAG retrieval     |   | RAG retrieval     |
   | RAG retrieval     |   +-------------------+   +-------------------+
   +---------+---------+             |                        |
             +-----------------------+------------------------+
                                     |
                           +---------v---------+
                           | Human Checkpoint  |
                           | approve/reject/   |
                           | deepen analysis   |
                           +---------+---------+
                                     |
                           +---------v---------+
                           | Synthesiser Agent |
                           |-------------------|
                           | report + summary  |
                           | contradictions    |
                           | recommendations   |
                           +---------+---------+
                                     |
                           +---------v---------+
                           | Report + Chat     |
                           | markdown + JSON   |
                           | RAG follow-up     |
                           +-------------------+

              Observability across all nodes: LangSmith traces + app logs
```

## End-to-End Data Flow

### 1. Analysis creation

1. User submits analysis metadata and documents from the Upload View.
2. `POST /api/analyses` stores metadata in SQLite and writes files to local disk.
3. Backend emits `analysis.created` and document ingestion events over SSE.

### 2. Document ingestion

1. Parser selects the loader based on file type.
2. Extracted text is normalized into document sections.
3. Sections are chunked with metadata preserving source provenance.
4. Chunks are embedded and inserted into a ChromaDB collection scoped to the analysis.

### 3. Parallel agent execution

1. LangGraph creates an analysis state object.
2. Graph fans out to Financial, Legal, and Market nodes.
3. Each node retrieves analysis-specific evidence and invokes domain tools.
4. Each node validates its output against a Pydantic schema.
5. Partial findings are persisted and streamed to the frontend.

### 4. Human checkpoint

1. Once all three specialist nodes complete or fail, the graph pauses.
2. Frontend shows a checkpoint panel with agent summaries and any errors.
3. User approves, rejects, or requests deeper analysis for selected areas.
4. Backend persists the decision and resumes or terminates the graph.

### 5. Synthesis

1. Synthesizer reads specialist outputs plus checkpoint instructions.
2. It detects contradictions and missing inputs.
3. It generates:
   - executive summary
   - category findings
   - risk scores
   - recommendations
   - markdown report
   - structured JSON summary
4. Outputs are stored and `report.completed` is emitted.

### 6. Follow-up chat

1. User asks a question in the Chat View.
2. Chat handler retrieves:
   - conversation history
   - relevant report sections
   - supporting source chunks
3. Response is generated with citations and stored in SQLite.

## Component Responsibilities

### Frontend

- collect uploads and metadata
- render streaming progress
- surface checkpoint actions
- render report and risk visualizations
- support follow-up chat and history navigation

### FastAPI API layer

- validate input
- manage uploads and analysis lifecycle
- expose report, history, chat, and checkpoint endpoints
- serve SSE streams for progress events

### LangGraph orchestration layer

- hold shared graph state
- coordinate fan-out/fan-in execution
- pause and resume around human checkpoint
- route deeper analysis requests

### Retrieval layer

- load analysis-scoped Chroma collection
- build query strategies per agent
- return evidence chunks with metadata for citations

### Persistence layer

- SQLite stores operational metadata
- file storage stores original uploads and optional derived artifacts
- Chroma stores embeddings and retrieval metadata

## State Boundaries

### Durable state

- analysis metadata
- document metadata
- agent outputs
- checkpoint decisions
- final report
- chat history

### Ephemeral state

- live SSE connections
- in-flight LangGraph node execution context
- tool intermediate results that are not part of persisted outputs

## Failure Handling

- parsing failures mark only affected documents unless the corpus becomes unusable
- agent failures are isolated and recorded at branch level
- synthesis proceeds with partial inputs if allowed by policy, but the report must disclose missing branches
- checkpoint decision is durable, enabling restart-safe resume
- SSE disconnections should not affect backend execution

## Deployment Notes

Phase 1 can run on a single machine:

- FastAPI app process
- Next.js app process
- SQLite database file
- Chroma persistence directory
- local file storage

For a later production deployment, replace local persistence layers independently:

- SQLite to Postgres
- local disk to object storage
- local background tasks to queue workers
- local Chroma to managed vector storage if scale requires it
