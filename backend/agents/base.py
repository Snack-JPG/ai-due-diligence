from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Type

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from backend.llm import get_chat_model


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_tool_calling_agent(
    *,
    system_prompt: str,
    user_prompt: str,
    tools: list[Any],
) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )
    return await executor.ainvoke({"input": user_prompt, "chat_history": []})


async def structure_agent_output(
    *,
    schema: Type[BaseModel],
    system_prompt: str,
    evidence_bundle: dict[str, Any],
) -> BaseModel:
    llm = get_chat_model()
    structured_llm = llm.with_structured_output(schema)
    repair_prompt = (
        f"{system_prompt}\n\n"
        "Convert the evidence bundle into the required schema. "
        "Use null when evidence is missing, preserve contradictions, and include citations."
    )
    return await structured_llm.ainvoke(
        [
            SystemMessage(content=repair_prompt),
            HumanMessage(content=json.dumps(evidence_bundle, ensure_ascii=True, default=str)),
        ]
    )
