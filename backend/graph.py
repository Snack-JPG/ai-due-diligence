from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.agents.financial import run_financial_agent
from backend.agents.legal import run_legal_agent
from backend.agents.market import run_market_agent
from backend.agents.synthesiser import run_synthesiser_agent
from backend.config import settings
from backend.database import db
from backend.document_processor import document_processor
from backend.schemas import AgentStatus, AnalysisStatus, CheckpointDecision, CheckpointStatus, ProgressEvent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GraphState(TypedDict, total=False):
    analysis_id: str
    analysis_context: dict[str, Any]
    documents: list[dict[str, Any]]
    financial_output: dict[str, Any] | None
    legal_output: dict[str, Any] | None
    market_output: dict[str, Any] | None
    checkpoint_decision: dict[str, Any] | None
    report_output: dict[str, Any] | None
    report_markdown: str | None
    chat_history: list[dict[str, Any]]
    follow_up_question: str | None
    errors: list[dict[str, Any]]
    event_log: list[dict[str, Any]]
    requested_focus_agents: list[str]
    deepen_count: int
    last_checkpoint_instruction: str | None


def emit_event(analysis_id: str, event_type: str, payload: dict[str, Any]) -> None:
    db.add_event(ProgressEvent(type=event_type, analysis_id=analysis_id, timestamp=utcnow(), payload=payload))


async def ingest_documents(state: GraphState) -> GraphState:
    analysis_id = state["analysis_id"]
    db.update_analysis_status(analysis_id, AnalysisStatus.processing_documents)
    processed = await asyncio.to_thread(document_processor.process_analysis, analysis_id)
    return {"documents": [item.__dict__ for item in processed]}


async def prepare_retrievers(state: GraphState) -> GraphState:
    analysis_id = state["analysis_id"]
    db.update_analysis_status(analysis_id, AnalysisStatus.running_agents)
    return {"documents": db.get_documents(analysis_id)}


async def _run_agent(
    state: GraphState,
    *,
    agent_name: Literal["financial", "legal", "market"],
    runner,
) -> GraphState:
    analysis_id = state["analysis_id"]
    if state.get("requested_focus_agents") and agent_name not in state.get("requested_focus_agents", []):
        return {}
    start_time = utcnow().isoformat()
    db.upsert_agent_run(analysis_id=analysis_id, agent_name=agent_name, status=AgentStatus.running, started_at=start_time)
    emit_event(analysis_id, "agent.started", {"agent": agent_name})
    checkpoint_instruction = state.get("last_checkpoint_instruction")
    try:
        payload = await runner(analysis_id, state["analysis_context"], checkpoint_instruction)
        output = payload.model_dump(mode="json")
        db.upsert_agent_run(
            analysis_id=analysis_id,
            agent_name=agent_name,
            status=AgentStatus.completed,
            completed_at=utcnow().isoformat(),
            raw_output_json=output,
        )
        emit_event(analysis_id, "agent.finding", {"agent": agent_name, "summary": output.get("summary"), "payload": output})
        emit_event(analysis_id, "agent.completed", {"agent": agent_name})
        return {f"{agent_name}_output": output}
    except Exception as exc:
        db.upsert_agent_run(
            analysis_id=analysis_id,
            agent_name=agent_name,
            status=AgentStatus.failed,
            completed_at=utcnow().isoformat(),
            error_message=str(exc),
        )
        emit_event(analysis_id, "agent.failed", {"agent": agent_name, "error": str(exc)})
        return {"errors": [*state.get("errors", []), {"agent": agent_name, "error": str(exc), "traceback": traceback.format_exc()}]}


async def financial_agent(state: GraphState) -> GraphState:
    return await _run_agent(state, agent_name="financial", runner=run_financial_agent)


async def legal_agent(state: GraphState) -> GraphState:
    return await _run_agent(state, agent_name="legal", runner=run_legal_agent)


async def market_agent(state: GraphState) -> GraphState:
    return await _run_agent(state, agent_name="market", runner=run_market_agent)


async def checkpoint_router(state: GraphState) -> GraphState:
    analysis_id = state["analysis_id"]
    db.update_analysis_status(analysis_id, AnalysisStatus.awaiting_checkpoint, checkpoint_status=CheckpointStatus.pending)
    emit_event(
        analysis_id,
        "checkpoint.required",
        {
            "financial": state.get("financial_output"),
            "legal": state.get("legal_output"),
            "market": state.get("market_output"),
            "errors": state.get("errors", []),
        },
    )
    return {}


async def human_checkpoint(state: GraphState) -> GraphState:
    decision_payload = interrupt(
        {
            "analysis_id": state["analysis_id"],
            "financial_output": state.get("financial_output"),
            "legal_output": state.get("legal_output"),
            "market_output": state.get("market_output"),
            "errors": state.get("errors", []),
        }
    )
    return {
        "checkpoint_decision": decision_payload,
        "requested_focus_agents": decision_payload.get("focus_agents", []),
        "last_checkpoint_instruction": decision_payload.get("reason"),
        "deepen_count": state.get("deepen_count", 0) + (1 if decision_payload.get("decision") == "deepen" else 0),
    }


def route_after_checkpoint(state: GraphState) -> str:
    decision = (state.get("checkpoint_decision") or {}).get("decision")
    if decision == "approve":
        return "synthesiser_agent"
    if decision == "reject":
        return "finalize_analysis"
    if decision == "deepen" and state.get("deepen_count", 0) <= settings.deepening_retry_limit:
        return "deeper_analysis_router"
    return "finalize_analysis"


async def deeper_analysis_router(state: GraphState) -> GraphState:
    emit_event(
        state["analysis_id"],
        "checkpoint.received",
        {"decision": "deepen", "focus_agents": state.get("requested_focus_agents", [])},
    )
    return {}


async def rerun_selected_agents(state: GraphState) -> GraphState:
    focus = state.get("requested_focus_agents") or ["financial", "legal", "market"]
    tasks = []
    if "financial" in focus:
        tasks.append(financial_agent(state))
    if "legal" in focus:
        tasks.append(legal_agent(state))
    if "market" in focus:
        tasks.append(market_agent(state))
    outputs: GraphState = {}
    for result in await asyncio.gather(*tasks):
        outputs.update(result)
    return outputs


async def synthesiser_agent(state: GraphState) -> GraphState:
    analysis_id = state["analysis_id"]
    db.update_analysis_status(analysis_id, AnalysisStatus.synthesizing)
    db.upsert_agent_run(
        analysis_id=analysis_id,
        agent_name="synthesiser",
        status=AgentStatus.running,
        started_at=utcnow().isoformat(),
    )
    emit_event(analysis_id, "synthesiser.started", {})
    report, markdown = await run_synthesiser_agent(
        state["analysis_context"],
        state.get("financial_output"),
        state.get("legal_output"),
        state.get("market_output"),
        state.get("checkpoint_decision"),
    )
    payload = report.model_dump(mode="json")
    db.upsert_agent_run(
        analysis_id=analysis_id,
        agent_name="synthesiser",
        status=AgentStatus.completed,
        completed_at=utcnow().isoformat(),
        raw_output_json=payload,
    )
    db.save_report(analysis_id, markdown, report)
    emit_event(analysis_id, "report.completed", {"overall_risk": report.overall_risk})
    return {"report_output": payload, "report_markdown": markdown}


async def finalize_analysis(state: GraphState) -> GraphState:
    analysis_id = state["analysis_id"]
    decision = (state.get("checkpoint_decision") or {}).get("decision")
    if decision == "reject":
        db.update_analysis_status(analysis_id, AnalysisStatus.failed, checkpoint_status=CheckpointStatus.rejected)
        emit_event(analysis_id, "analysis.failed", {"reason": state.get("checkpoint_decision", {}).get("reason")})
    elif state.get("report_output"):
        db.update_analysis_status(analysis_id, AnalysisStatus.completed, checkpoint_status=CheckpointStatus.approved)
    return {}


class GraphManager:
    def __init__(self) -> None:
        self.checkpointer = SqliteSaver.from_conn_string(str(settings.sqlite_checkpoint_path))
        self.graph = self._build_graph().compile(checkpointer=self.checkpointer)

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(GraphState)
        graph.add_node("ingest_documents", ingest_documents)
        graph.add_node("prepare_retrievers", prepare_retrievers)
        graph.add_node("financial_agent", financial_agent)
        graph.add_node("legal_agent", legal_agent)
        graph.add_node("market_agent", market_agent)
        graph.add_node("checkpoint_router", checkpoint_router)
        graph.add_node("human_checkpoint", human_checkpoint)
        graph.add_node("deeper_analysis_router", deeper_analysis_router)
        graph.add_node("rerun_selected_agents", rerun_selected_agents)
        graph.add_node("synthesiser_agent", synthesiser_agent)
        graph.add_node("finalize_analysis", finalize_analysis)

        graph.add_edge(START, "ingest_documents")
        graph.add_edge("ingest_documents", "prepare_retrievers")
        graph.add_edge("prepare_retrievers", "financial_agent")
        graph.add_edge("prepare_retrievers", "legal_agent")
        graph.add_edge("prepare_retrievers", "market_agent")
        graph.add_edge("financial_agent", "checkpoint_router")
        graph.add_edge("legal_agent", "checkpoint_router")
        graph.add_edge("market_agent", "checkpoint_router")
        graph.add_edge("checkpoint_router", "human_checkpoint")
        graph.add_conditional_edges("human_checkpoint", route_after_checkpoint)
        graph.add_edge("deeper_analysis_router", "rerun_selected_agents")
        graph.add_edge("rerun_selected_agents", "checkpoint_router")
        graph.add_edge("synthesiser_agent", "finalize_analysis")
        graph.add_edge("finalize_analysis", END)
        return graph

    async def start_analysis(self, analysis_id: str, analysis_context: dict[str, Any]) -> None:
        await self.graph.ainvoke(
            {
                "analysis_id": analysis_id,
                "analysis_context": analysis_context,
                "errors": [],
                "event_log": [],
                "deepen_count": 0,
                "requested_focus_agents": [],
            },
            config={"configurable": {"thread_id": analysis_id}},
        )

    async def resume_after_checkpoint(self, analysis_id: str, decision: CheckpointDecision) -> None:
        checkpoint_status = {
            "approve": CheckpointStatus.approved,
            "reject": CheckpointStatus.rejected,
            "deepen": CheckpointStatus.deepen_requested,
        }[decision.decision]
        next_status = {
            "approve": AnalysisStatus.synthesizing,
            "reject": AnalysisStatus.failed,
            "deepen": AnalysisStatus.awaiting_checkpoint,
        }[decision.decision]
        db.update_analysis_status(
            analysis_id,
            next_status,
            checkpoint_status=checkpoint_status,
        )
        emit_event(
            analysis_id,
            "checkpoint.received",
            {"decision": decision.decision, "reason": decision.reason, "focus_agents": decision.focus_agents},
        )
        await self.graph.ainvoke(
            Command(
                resume={
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "focus_agents": decision.focus_agents,
                }
            ),
            config={"configurable": {"thread_id": analysis_id}},
        )


graph_manager = GraphManager()
