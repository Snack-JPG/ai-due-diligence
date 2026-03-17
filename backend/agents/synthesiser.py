from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.agents.base import structure_agent_output
from backend.schemas import DueDiligenceReport


SYSTEM_PROMPT = """
You are the Synthesiser Agent in a due diligence workflow.

Your job is to combine the outputs of the Financial Analyst Agent, Legal Analyst Agent, and Market Research Agent into a coherent and decision-useful due diligence report.

You must:
- generate an executive summary suitable for an investor or analyst
- present detailed findings by category
- assign category risk scores from 1 to 10
- assign an overall risk score from 1 to 10
- highlight contradictions across agent outputs
- provide clear recommendations and follow-up questions
- disclose gaps, failed branches, and low-confidence areas

Rules:
- do not invent evidence not present in agent outputs or source citations
- preserve nuance when evidence is conflicting
- if an agent failed or returned partial data, state that explicitly
- recommendations must be actionable and tied to observed findings
- return both markdown report content and structured summary data
""".strip()


def render_report_markdown(
    report: DueDiligenceReport,
    financial_output: dict[str, Any] | None,
    legal_output: dict[str, Any] | None,
    market_output: dict[str, Any] | None,
) -> str:
    lines = [
        "# Due Diligence Report",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        "## Financial Findings",
        report.financial.summary,
    ]
    for finding in report.financial.key_findings:
        lines.append(f"- {finding}")
    lines.extend(["", "## Legal Findings", report.legal.summary])
    for finding in report.legal.key_findings:
        lines.append(f"- {finding}")
    lines.extend(["", "## Market Findings", report.market.summary])
    for finding in report.market.key_findings:
        lines.append(f"- {finding}")
    lines.extend(["", "## Contradictions"])
    if report.contradictions:
        for contradiction in report.contradictions:
            lines.append(f"- {contradiction.topic}: {contradiction.description}")
    else:
        lines.append("- No material contradictions identified from available evidence.")
    lines.extend(["", "## Recommendations"])
    for recommendation in report.recommendations:
        lines.append(f"- [{recommendation.priority}] {recommendation.action}: {recommendation.rationale}")
    lines.extend(
        [
            "",
            "## Risk Scores",
            f"- Overall risk: {report.overall_risk}/10",
            f"- Financial risk signals: {len(report.financial.flags)} flagged items",
            f"- Legal risk signals: {len(report.legal.flags)} flagged items",
            f"- Market risk signals: {len(report.market.flags)} flagged items",
            "",
            "## Source Notes",
            f"- Financial data attached: {'yes' if financial_output else 'no'}",
            f"- Legal data attached: {'yes' if legal_output else 'no'}",
            f"- Market data attached: {'yes' if market_output else 'no'}",
            "",
            f"_Generated at {report.generated_at.isoformat()}_",
        ]
    )
    return "\n".join(lines)


async def run_synthesiser_agent(
    analysis_context: dict[str, Any],
    financial_output: dict[str, Any] | None,
    legal_output: dict[str, Any] | None,
    market_output: dict[str, Any] | None,
    checkpoint_decision: dict[str, Any] | None,
) -> tuple[DueDiligenceReport, str]:
    report = await structure_agent_output(
        schema=DueDiligenceReport,
        system_prompt=SYSTEM_PROMPT,
        evidence_bundle={
            "analysis_context": analysis_context,
            "financial_output": financial_output,
            "legal_output": legal_output,
            "market_output": market_output,
            "checkpoint_decision": checkpoint_decision,
            "generated_at_hint": datetime.now(timezone.utc).isoformat(),
        },
    )
    if report.generated_at.tzinfo is None:
        report.generated_at = report.generated_at.replace(tzinfo=timezone.utc)
    markdown = render_report_markdown(report, financial_output, legal_output, market_output)
    return report, markdown
