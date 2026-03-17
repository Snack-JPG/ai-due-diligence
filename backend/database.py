from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.config import ensure_directories, settings
from backend.schemas import (
    AgentResultEnvelope,
    AgentStatus,
    AnalysisDetail,
    AnalysisListItem,
    AnalysisStatus,
    CheckpointDecision,
    CheckpointStatus,
    DueDiligenceReport,
    PaginatedAnalyses,
    ProgressEvent,
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        ensure_directories()
        self.db_path = db_path or settings.sqlite_database_path
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    company_name TEXT,
                    industry TEXT,
                    region TEXT,
                    focus_areas_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    checkpoint_status TEXT NOT NULL DEFAULT 'pending',
                    report_markdown TEXT,
                    report_summary_json TEXT,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    storage_path TEXT NOT NULL,
                    parse_status TEXT NOT NULL,
                    page_count INTEGER,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    raw_output_json TEXT,
                    error_message TEXT,
                    trace_id TEXT
                );

                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT,
                    requested_focus_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}'
                );
                """
            )

    def create_analysis(
        self,
        *,
        name: str,
        company_name: str | None,
        industry: str | None,
        region: str | None,
        focus_areas: list[str],
    ) -> dict[str, Any]:
        analysis_id = str(uuid.uuid4())
        now = utcnow()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO analyses (
                    id, name, status, company_name, industry, region,
                    focus_areas_json, created_at, updated_at, checkpoint_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    name,
                    AnalysisStatus.created.value,
                    company_name,
                    industry,
                    region,
                    json.dumps(focus_areas),
                    now,
                    now,
                    CheckpointStatus.pending.value,
                ),
            )
        return {"id": analysis_id, "created_at": datetime.fromisoformat(now)}

    def update_analysis_status(
        self,
        analysis_id: str,
        status: AnalysisStatus,
        *,
        checkpoint_status: CheckpointStatus | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE analyses
                SET status = ?, checkpoint_status = COALESCE(?, checkpoint_status),
                    error_message = COALESCE(?, error_message), updated_at = ?
                WHERE id = ?
                """,
                (status.value, checkpoint_status.value if checkpoint_status else None, error_message, utcnow(), analysis_id),
            )

    def save_document(
        self,
        *,
        analysis_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_path: str,
    ) -> str:
        document_id = str(uuid.uuid4())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, analysis_id, filename, content_type, size_bytes, storage_path,
                    parse_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, analysis_id, filename, content_type, size_bytes, storage_path, "pending", utcnow()),
            )
        return document_id

    def update_document_parse_status(self, document_id: str, parse_status: str, page_count: int | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE documents SET parse_status = ?, page_count = COALESCE(?, page_count) WHERE id = ?",
                (parse_status, page_count, document_id),
            )

    def get_documents(self, analysis_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM documents WHERE analysis_id = ? ORDER BY created_at ASC", (analysis_id,)).fetchall()
        return [dict(row) for row in rows]

    def upsert_agent_run(
        self,
        *,
        analysis_id: str,
        agent_name: str,
        status: AgentStatus,
        started_at: str | None = None,
        completed_at: str | None = None,
        raw_output_json: dict[str, Any] | None = None,
        error_message: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM agent_runs WHERE analysis_id = ? AND agent_name = ?",
                (analysis_id, agent_name),
            ).fetchone()
            payload = json.dumps(raw_output_json) if raw_output_json is not None else None
            if existing:
                conn.execute(
                    """
                    UPDATE agent_runs
                    SET status = ?, started_at = COALESCE(?, started_at),
                        completed_at = COALESCE(?, completed_at),
                        raw_output_json = COALESCE(?, raw_output_json),
                        error_message = ?, trace_id = COALESCE(?, trace_id)
                    WHERE analysis_id = ? AND agent_name = ?
                    """,
                    (
                        status.value,
                        started_at,
                        completed_at,
                        payload,
                        error_message,
                        trace_id,
                        analysis_id,
                        agent_name,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO agent_runs (
                        id, analysis_id, agent_name, status, started_at,
                        completed_at, raw_output_json, error_message, trace_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        analysis_id,
                        agent_name,
                        status.value,
                        started_at,
                        completed_at,
                        payload,
                        error_message,
                        trace_id,
                    ),
                )

    def list_agent_runs(self, analysis_id: str) -> dict[str, AgentResultEnvelope]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_runs WHERE analysis_id = ? ORDER BY started_at ASC",
                (analysis_id,),
            ).fetchall()
        runs: dict[str, AgentResultEnvelope] = {}
        for row in rows:
            payload = json.loads(row["raw_output_json"]) if row["raw_output_json"] else None
            runs[row["agent_name"]] = AgentResultEnvelope(
                agent_name=row["agent_name"],
                status=row["status"],
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                trace_id=row["trace_id"],
                error_message=row["error_message"],
                payload=payload,
            )
        return runs

    def save_checkpoint_decision(self, analysis_id: str, decision: CheckpointDecision) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO checkpoints (id, analysis_id, decision, reason, requested_focus_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    analysis_id,
                    decision.decision,
                    decision.reason,
                    json.dumps(decision.focus_agents),
                    decision.requested_at.isoformat(),
                ),
            )

    def get_latest_checkpoint(self, analysis_id: str) -> CheckpointDecision | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE analysis_id = ? ORDER BY created_at DESC LIMIT 1",
                (analysis_id,),
            ).fetchone()
        if not row:
            return None
        return CheckpointDecision(
            decision=row["decision"],
            reason=row["reason"],
            focus_agents=json.loads(row["requested_focus_json"] or "[]"),
            requested_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_report(self, analysis_id: str, markdown: str, summary: DueDiligenceReport) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE analyses
                SET report_markdown = ?, report_summary_json = ?, updated_at = ?, status = ?, checkpoint_status = ?
                WHERE id = ?
                """,
                (
                    markdown,
                    summary.model_dump_json(),
                    utcnow(),
                    AnalysisStatus.completed.value,
                    CheckpointStatus.approved.value,
                    analysis_id,
                ),
            )

    def add_chat_message(self, analysis_id: str, role: str, content: str, citations_json: list[dict[str, Any]] | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, analysis_id, role, content, citations_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), analysis_id, role, content, json.dumps(citations_json), utcnow()),
            )

    def get_chat_messages(self, analysis_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE analysis_id = ? ORDER BY created_at ASC",
                (analysis_id,),
            ).fetchall()
        return [
            {**dict(row), "citations_json": json.loads(row["citations_json"]) if row["citations_json"] else []}
            for row in rows
        ]

    def add_event(self, event: ProgressEvent) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO events (analysis_id, type, timestamp, payload_json) VALUES (?, ?, ?, ?)",
                (event.analysis_id, event.type, event.timestamp.isoformat(), json.dumps(event.payload)),
            )
            return int(cursor.lastrowid)

    def get_events(self, analysis_id: str, last_event_id: int = 0) -> list[ProgressEvent]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE analysis_id = ? AND id > ? ORDER BY id ASC",
                (analysis_id, last_event_id),
            ).fetchall()
        return [
            ProgressEvent(
                id=row["id"],
                type=row["type"],
                analysis_id=row["analysis_id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                payload=json.loads(row["payload_json"] or "{}"),
            )
            for row in rows
        ]

    def get_analysis(self, analysis_id: str) -> AnalysisDetail | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if not row:
            return None
        report_available = row["report_markdown"] is not None and row["report_summary_json"] is not None
        return AnalysisDetail(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            checkpoint_status=row["checkpoint_status"],
            company_name=row["company_name"],
            industry=row["industry"],
            region=row["region"],
            focus_areas=json.loads(row["focus_areas_json"] or "[]"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            documents=self.get_documents(analysis_id),
            agents=self.list_agent_runs(analysis_id),
            report_available=report_available,
            events=self.get_events(analysis_id),
            error_message=row["error_message"],
        )

    def get_report(self, analysis_id: str) -> tuple[str, DueDiligenceReport] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT report_markdown, report_summary_json FROM analyses WHERE id = ?",
                (analysis_id,),
            ).fetchone()
        if not row or not row["report_markdown"] or not row["report_summary_json"]:
            return None
        return row["report_markdown"], DueDiligenceReport.model_validate_json(row["report_summary_json"])

    def list_analyses(self, *, q: str | None, status: str | None, page: int, page_size: int) -> PaginatedAnalyses:
        clauses = []
        params: list[Any] = []
        if q:
            clauses.append("(name LIKE ? OR company_name LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        if status:
            clauses.append("status = ?")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        offset = (page - 1) * page_size
        with self.connection() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM analyses {where_sql}", params).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT id, name, status, checkpoint_status, company_name, created_at, updated_at
                FROM analyses
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        items = [
            AnalysisListItem(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                checkpoint_status=row["checkpoint_status"],
                company_name=row["company_name"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
        return PaginatedAnalyses(items=items, total=total, page=page, page_size=page_size)


db = Database()
