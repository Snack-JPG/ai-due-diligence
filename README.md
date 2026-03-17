# AI Due Diligence Agent

A production-grade portfolio project that demonstrates a LangGraph multi-agent system for automated business due diligence.

Users upload company materials such as financials, contracts, pitch decks, reports, and spreadsheets. The system indexes the documents, runs specialist AI agents in parallel, pauses for human review, and then produces a structured due diligence report with follow-up chat.

## What This Demonstrates

- LangGraph `StateGraph` orchestration with parallel branches
- specialist tool-calling agents with typed outputs
- retrieval-augmented generation over uploaded documents
- human-in-the-loop checkpoints and resumable workflows
- real-time streaming status updates to a web frontend
- structured report generation with risk scoring
- LangSmith tracing for observability
- multi-model architecture with provider swap support

## Agent Lineup

- Financial Analyst Agent: extracts core financial metrics, anomalies, runway, and unit economics
- Legal Analyst Agent: reviews contracts, IP, liability, and compliance exposure
- Market Research Agent: validates company claims against market reality and recent news
- Synthesiser Agent: turns all findings into an executive-grade due diligence report

## Tech Stack

- Backend: Python 3.12, FastAPI
- Agent orchestration: LangChain, LangGraph, LangSmith
- LLM: OpenAI GPT-4o by default
- Embeddings: `text-embedding-3-small`
- Vector store: ChromaDB
- Metadata store: SQLite
- Frontend: Next.js 15, TypeScript, Tailwind, shadcn/ui

## Core Product Flow

1. Upload documents and create an analysis.
2. Parse, chunk, embed, and index documents in ChromaDB.
3. Run Financial, Legal, and Market agents in parallel.
4. Pause for a human checkpoint.
5. Run the Synthesiser Agent to generate the final report.
6. Ask grounded follow-up questions in chat.

## Views

- Upload View
- Analysis View
- Report View
- Chat View
- History View

## API Surface

- `POST /api/analyses`
- `GET /api/analyses/:id`
- `GET /api/analyses/:id/report`
- `POST /api/analyses/:id/chat`
- `GET /api/analyses`
- `POST /api/analyses/:id/checkpoint`

## Project Docs

- [SPEC.md](/Users/austin/Desktop/ai-due-diligence/SPEC.md)
- [ARCHITECTURE.md](/Users/austin/Desktop/ai-due-diligence/ARCHITECTURE.md)
- [AGENTS.md](/Users/austin/Desktop/ai-due-diligence/AGENTS.md)
- [SCHEMAS.md](/Users/austin/Desktop/ai-due-diligence/SCHEMAS.md)

## Suggested Local Setup

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

## Environment Variables

```bash
OPENAI_API_KEY=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=ai-due-diligence
MODEL_PROVIDER=openai
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
CHROMA_PERSIST_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
SQLITE_DATABASE_URL=sqlite:///./data/app.db
```

## Repository Layout

```text
backend/
frontend/
data/
tests/
SPEC.md
ARCHITECTURE.md
AGENTS.md
SCHEMAS.md
README.md
```

## Screenshots

Placeholders for future screenshots:

- `docs/screenshots/upload-view.png`
- `docs/screenshots/analysis-view.png`
- `docs/screenshots/report-view.png`
- `docs/screenshots/chat-view.png`

## Current Status

Phase 1 documentation is complete and implementation-ready. The next step is scaffolding the backend and frontend according to the contracts in the spec.
