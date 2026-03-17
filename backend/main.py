from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import ensure_directories, settings
from backend.database import db
from backend.document_processor import infer_content_type, sanitize_filename
from backend.graph import graph_manager
from backend.llm import get_chat_model
from backend.retrieval import retrieval_service
from backend.schemas import (
    AnalysisCreateResponse,
    AnalysisDetail,
    AnalysisStatus,
    ChatRequest,
    ChatResponse,
    CheckpointDecision,
    PaginatedAnalyses,
    ProgressEvent,
    ReportResponse,
)


app = FastAPI(title="AI Due Diligence Agent", default_response_class=ORJSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".csv", ".txt"}


@app.on_event("startup")
async def on_startup() -> None:
    ensure_directories()


async def run_initial_analysis(analysis_id: str, analysis_context: dict[str, str | list[str] | None]) -> None:
    try:
        await graph_manager.start_analysis(analysis_id, analysis_context)
    except Exception as exc:
        db.update_analysis_status(analysis_id, AnalysisStatus.failed, error_message=str(exc))
        db.add_event(
            ProgressEvent(
                type="analysis.failed",
                analysis_id=analysis_id,
                timestamp=utcnow(),
                payload={"error": str(exc)},
            )
        )


@app.post("/api/analyses", response_model=AnalysisCreateResponse)
async def create_analysis(
    name: str = Form(...),
    company_name: str | None = Form(default=None),
    industry: str | None = Form(default=None),
    region: str | None = Form(default=None),
    focus_areas: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
) -> AnalysisCreateResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    if len(files) > settings.max_files_per_analysis:
        raise HTTPException(status_code=400, detail="Too many files")
    focus_list = json.loads(focus_areas) if focus_areas else []
    total_size = 0
    created = db.create_analysis(
        name=name,
        company_name=company_name,
        industry=industry,
        region=region,
        focus_areas=focus_list,
    )
    analysis_id = created["id"]
    analysis_dir = settings.upload_dir / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        content = await upload.read()
        size = len(content)
        total_size += size
        if size > settings.max_file_size_bytes:
            raise HTTPException(status_code=400, detail=f"{upload.filename} exceeds file size limit")
        if total_size > settings.max_combined_size_bytes:
            raise HTTPException(status_code=400, detail="Combined upload size exceeds limit")
        filename = sanitize_filename(upload.filename or "document")
        if Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type for {upload.filename}")
        path = analysis_dir / filename
        path.write_bytes(content)
        db.save_document(
            analysis_id=analysis_id,
            filename=upload.filename or filename,
            content_type=upload.content_type or infer_content_type(filename),
            size_bytes=size,
            storage_path=str(path),
        )
    db.update_analysis_status(analysis_id, AnalysisStatus.processing_documents)
    db.add_event(
        ProgressEvent(type="analysis.created", analysis_id=analysis_id, timestamp=utcnow(), payload={"name": name})
    )
    asyncio.create_task(
        run_initial_analysis(
            analysis_id,
            {
                "company_name": company_name,
                "industry": industry,
                "region": region,
                "focus_areas": focus_list,
            },
        )
    )
    return AnalysisCreateResponse(
        id=analysis_id,
        status=AnalysisStatus.processing_documents,
        created_at=created["created_at"],
    )


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(analysis_id: str) -> AnalysisDetail:
    analysis = db.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.get("/api/analyses/{analysis_id}/report", response_model=ReportResponse)
async def get_report(analysis_id: str) -> ReportResponse:
    report = db.get_report(analysis_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not available")
    markdown, summary = report
    return ReportResponse(analysis_id=analysis_id, markdown=markdown, summary=summary)


@app.get("/api/analyses", response_model=PaginatedAnalyses)
async def list_analyses(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedAnalyses:
    return db.list_analyses(q=q, status=status, page=page, page_size=page_size)


@app.post("/api/analyses/{analysis_id}/checkpoint")
async def submit_checkpoint(
    analysis_id: str,
    decision: CheckpointDecision,
) -> dict[str, str]:
    if not db.get_analysis(analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.save_checkpoint_decision(analysis_id, decision)
    asyncio.create_task(graph_manager.resume_after_checkpoint(analysis_id, decision))
    return {"status": "accepted"}


@app.post("/api/analyses/{analysis_id}/chat", response_model=ChatResponse)
async def chat(analysis_id: str, request: ChatRequest) -> ChatResponse:
    analysis = db.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    report = db.get_report(analysis_id)
    if not report:
        raise HTTPException(status_code=400, detail="Report is not available yet")
    history = db.get_chat_messages(analysis_id)
    retrieved = retrieval_service.search(analysis_id, request.message, preferred_types=None)
    retrieved_context = retrieval_service.format_chunks(retrieved)
    markdown, summary = report
    llm = get_chat_model()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content="You are a grounded due diligence assistant. Use the final report, chat history, and retrieved source chunks. Cite available evidence and say when the answer is unsupported."
            ),
            HumanMessage(
                content=json.dumps(
                    {
                        "question": request.message,
                        "report_summary": summary.model_dump(mode="json"),
                        "report_markdown": markdown,
                        "chat_history": history,
                        "retrieved_context": retrieved_context,
                    },
                    default=str,
                )
            ),
        ]
    )
    citations = [item["citation"] for item in retrieved[:4]] if request.include_citations else []
    db.add_chat_message(analysis_id, "user", request.message)
    db.add_chat_message(analysis_id, "assistant", response.content, citations)
    return ChatResponse(answer=response.content, citations=citations, trace_id=None)


async def event_stream(analysis_id: str, last_event_id: int) -> AsyncIterator[str]:
    cursor = last_event_id
    while True:
        events = db.get_events(analysis_id, cursor)
        if events:
            for event in events:
                cursor = max(cursor, event.id or 0)
                yield f"id: {event.id}\n"
                yield f"event: {event.type}\n"
                yield f"data: {event.model_dump_json()}\n\n"
        else:
            yield ": keep-alive\n\n"
        await asyncio.sleep(1)


@app.get("/api/analyses/{analysis_id}/events")
async def sse_events(analysis_id: str, last_event_id: int = Query(default=0)) -> StreamingResponse:
    if not db.get_analysis(analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return StreamingResponse(event_stream(analysis_id, last_event_id), media_type="text/event-stream")
