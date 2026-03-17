from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from backend.config import settings


def configure_tracing() -> None:
    if settings.langsmith_api_key and settings.langsmith_tracing:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)


def get_chat_model(temperature: float = 0) -> ChatOpenAI:
    configure_tracing()
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
    )
