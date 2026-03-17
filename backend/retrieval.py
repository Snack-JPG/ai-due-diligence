from __future__ import annotations

from typing import Any

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from backend.config import settings
from backend.schemas import Citation


class RetrievalService:
    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

    def _store(self, analysis_id: str) -> Chroma:
        return Chroma(
            collection_name=f"analysis_{analysis_id}",
            embedding_function=self.embeddings,
            persist_directory=str(settings.chroma_persist_dir),
            client_settings=ChromaSettings(anonymized_telemetry=False),
        )

    def search(
        self,
        analysis_id: str,
        query: str,
        *,
        preferred_types: list[str] | None = None,
        k: int | None = None,
    ) -> list[dict[str, Any]]:
        vectorstore = self._store(analysis_id)
        filters = None
        if preferred_types:
            filters = {"document_type": {"$in": preferred_types}}
        docs = vectorstore.similarity_search(query, k=k or settings.top_k_retrieval, filter=filters)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "citation": Citation(
                    document_id=doc.metadata.get("document_id"),
                    filename=doc.metadata.get("filename", "Unknown"),
                    locator=doc.metadata.get("locator") or f"Chunk {doc.metadata.get('chunk_index', 0)}",
                ).model_dump(),
            }
            for doc in docs
        ]

    def format_chunks(self, chunks: list[dict[str, Any]]) -> str:
        rendered = []
        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk["metadata"]
            rendered.append(
                "\n".join(
                    [
                        f"[Chunk {idx}]",
                        f"Filename: {meta.get('filename', 'Unknown')}",
                        f"Locator: {meta.get('locator', 'Unknown')}",
                        chunk["content"],
                    ]
                )
            )
        return "\n\n".join(rendered)


retrieval_service = RetrievalService()
