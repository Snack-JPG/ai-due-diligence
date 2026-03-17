from __future__ import annotations

from typing import Any

from backend.agents.base import run_tool_calling_agent, structure_agent_output
from backend.agents.tools import build_rag_tool, build_table_parser_tool, calculator_tool
from backend.schemas import FinancialMetrics


SYSTEM_PROMPT = """
You are the Financial Analyst Agent in a due diligence workflow.

Your job is to extract and evaluate the company's financial health from uploaded materials such as P&L statements, balance sheets, cash flow statements, board updates, KPI dashboards, budgets, and pitch decks.

You must:
- extract revenue, gross margin, net margin, burn rate, runway, growth rate, and unit economics when available
- identify anomalies, inconsistencies between documents, and missing financial disclosures
- prefer explicit values over inferred values
- use calculator and table parsing tools when numeric calculations are required
- cite the evidence for every metric and risk flag
- return only structured output matching the required schema

Rules:
- if a metric is not directly supported by evidence, set it to null
- do not guess dates, currencies, or time periods
- if multiple values are present across documents, surface the discrepancy as a flag
- if calculations are performed, include the formula description in the rationale field
- distinguish historical metrics from forward-looking projections
""".strip()


async def run_financial_agent(
    analysis_id: str,
    analysis_context: dict[str, Any],
    checkpoint_instruction: str | None = None,
) -> FinancialMetrics:
    rag_tool = build_rag_tool(analysis_id, preferred_types=["xlsx", "csv", "pdf", "txt", "docx"])
    table_tool = build_table_parser_tool(analysis_id)
    retrieved_chunks = {
        "financial_overview": rag_tool.invoke("Revenue, margins, burn, runway, unit economics"),
        "forecasting": rag_tool.invoke("Budget, operating plan, investor update, revenue projection"),
    }
    tool_run = await run_tool_calling_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=(
            "Analysis context:\n"
            f"{analysis_context}\n\n"
            "Retrieved financial evidence:\n"
            f"{retrieved_chunks}\n\n"
            "Additional instruction from checkpoint, if any:\n"
            f"{checkpoint_instruction}\n\n"
            "Use the available tools if you need calculations or deeper table extraction. "
            "Return concise analysis notes with explicit evidence references."
        ),
        tools=[rag_tool, table_tool, calculator_tool],
    )
    return await structure_agent_output(
        schema=FinancialMetrics,
        system_prompt=SYSTEM_PROMPT,
        evidence_bundle={
            "analysis_context": analysis_context,
            "retrieved_chunks": retrieved_chunks,
            "tool_outputs": tool_run,
            "checkpoint_instruction": checkpoint_instruction,
        },
    )
