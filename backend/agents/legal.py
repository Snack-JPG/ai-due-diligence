from __future__ import annotations

from typing import Any

from backend.agents.base import run_tool_calling_agent, structure_agent_output
from backend.agents.tools import build_rag_tool, keyword_extraction_tool
from backend.schemas import LegalFindings


SYSTEM_PROMPT = """
You are the Legal Analyst Agent in a due diligence workflow.

Your job is to extract legally material terms and identify risks in the uploaded company documents.

Focus on:
- contract terms
- IP ownership and assignment
- liability limitations
- indemnities
- termination rights
- exclusivity clauses
- employment and contractor IP provisions
- privacy, regulatory, and compliance issues
- jurisdiction and governing law risks

You must:
- summarize key legal findings in structured form
- assign a risk score based on severity and evidence quality
- flag unusual terms, missing protections, or incomplete documentation
- cite source documents for every major finding

Rules:
- do not provide legal advice or claim enforceability beyond what the text supports
- if a document appears partial or unsigned, mark that limitation
- if key protections are absent, state that the absence is based on available materials only
- return only the required structured schema
""".strip()


async def run_legal_agent(
    analysis_id: str,
    analysis_context: dict[str, Any],
    checkpoint_instruction: str | None = None,
) -> LegalFindings:
    rag_tool = build_rag_tool(analysis_id, preferred_types=["pdf", "docx", "txt"])
    retrieved_chunks = {
        "contracts": rag_tool.invoke("Contracts, terms, liabilities, indemnities, termination rights"),
        "ip_and_compliance": rag_tool.invoke("IP ownership, assignment, employment, privacy, compliance"),
    }
    tool_run = await run_tool_calling_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=(
            "Analysis context:\n"
            f"{analysis_context}\n\n"
            "Retrieved legal evidence:\n"
            f"{retrieved_chunks}\n\n"
            "Additional instruction from checkpoint, if any:\n"
            f"{checkpoint_instruction}\n\n"
            "Use the keyword extraction tool when useful. Return analysis notes only."
        ),
        tools=[rag_tool, keyword_extraction_tool],
    )
    return await structure_agent_output(
        schema=LegalFindings,
        system_prompt=SYSTEM_PROMPT,
        evidence_bundle={
            "analysis_context": analysis_context,
            "retrieved_chunks": retrieved_chunks,
            "tool_outputs": tool_run,
            "checkpoint_instruction": checkpoint_instruction,
        },
    )
