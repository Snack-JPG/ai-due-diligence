from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.agents.base import run_tool_calling_agent, structure_agent_output
from backend.agents.tools import build_rag_tool, web_search_tool
from backend.schemas import MarketAnalysis


SYSTEM_PROMPT = """
You are the Market Research Agent in a due diligence workflow.

Your job is to assess the target company's market environment using both uploaded materials and external research.

Focus on:
- market size and growth
- industry trends
- competitive landscape
- recent news
- customer or segment dynamics
- whether company claims appear supported or overstated

You must:
- compare company assertions in uploaded materials against external sources
- identify notable competitors and positioning
- summarize recent relevant news and industry developments
- assign a market risk score
- clearly label what comes from uploaded documents versus external research

Rules:
- include freshness dates for external evidence
- do not overstate certainty when market data is mixed or sparse
- distinguish factual findings from inference
- return only the required structured schema
""".strip()


async def run_market_agent(
    analysis_id: str,
    analysis_context: dict[str, Any],
    checkpoint_instruction: str | None = None,
) -> MarketAnalysis:
    rag_tool = build_rag_tool(analysis_id, preferred_types=["pdf", "docx", "txt", "xlsx", "csv"])
    internal_claims = rag_tool.invoke("Market size claims, competitors, positioning, customers, growth narrative")
    company_name = analysis_context.get("company_name") or "target company"
    external = web_search_tool.invoke(f"{company_name} market size competitors recent news")
    external["freshness_date"] = datetime.now(timezone.utc).date().isoformat()
    tool_run = await run_tool_calling_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=(
            "Analysis context:\n"
            f"{analysis_context}\n\n"
            "Uploaded-document evidence:\n"
            f"{internal_claims}\n\n"
            "External research and web results:\n"
            f"{external}\n\n"
            "Additional instruction from checkpoint, if any:\n"
            f"{checkpoint_instruction}\n\n"
            "Use the web search tool if more recent validation is needed. Return analysis notes only."
        ),
        tools=[rag_tool, web_search_tool],
    )
    return await structure_agent_output(
        schema=MarketAnalysis,
        system_prompt=SYSTEM_PROMPT,
        evidence_bundle={
            "analysis_context": analysis_context,
            "retrieved_chunks": internal_claims,
            "tool_outputs": {"external": external, "agent_execution": tool_run},
            "checkpoint_instruction": checkpoint_instruction,
        },
    )
