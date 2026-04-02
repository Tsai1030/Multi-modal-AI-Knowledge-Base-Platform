import json
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.rag.chroma_adapter import scoped_allowed_full_doc_ids
from app.repositories.document_repository import DocumentRepository
from app.schemas.query import SSEEvent

if TYPE_CHECKING:
    from raganything import RAGAnything

    from app.rag.llm_adapter import OllamaLLMAdapter
    from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)
STREAM_CHUNK_SIZE = 24
EMPTY_RAG_MESSAGE = (
    "No indexed context was found for this question. "
    "Please make sure your document is completed and try a more specific question."
)


class RAGQueryService:
    """Run RAG query and stream final answer through SSE."""

    def __init__(
        self,
        rag_engine: "RAGAnything",
        llm_adapter: "OllamaLLMAdapter",
        conversation_service: "ConversationService",
        document_repo: DocumentRepository,
    ) -> None:
        self._rag = rag_engine
        self._llm = llm_adapter
        self._conv_svc = conversation_service
        self._doc_repo = document_repo

    async def query_stream(
        self,
        session_id: uuid.UUID,
        question: str,
        mode: str = "hybrid",
        user_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        try:
            conv_context = await self._conv_svc.get_conversation_context(session_id, question)
            effective_mode = self._select_mode(mode)
            await self._conv_svc.save_user_message(session_id, question, effective_mode)
            session_doc_scope = await self._resolve_session_doc_scope(session_id)

            scope_ctx = (
                scoped_allowed_full_doc_ids(session_doc_scope)
                if session_doc_scope is not None
                else nullcontext()
            )
            with scope_ctx:
                query_result = await self._query_with_fallback(
                    question=question,
                    mode=effective_mode,
                    conversation_history=conv_context,
                )
        except Exception as exc:
            logger.error("RAG query failed for session %s: %s", session_id, exc)
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        try:
            full_response = ""
            if _is_async_iterable(query_result):
                async for token in query_result:
                    full_response += token
                    yield _sse_json(SSEEvent(type="token", content=token))
            else:
                answer = str(query_result).strip() or EMPTY_RAG_MESSAGE
                for token in _chunk_text(answer):
                    full_response += token
                    yield _sse_json(SSEEvent(type="token", content=token))

            if not full_response.strip():
                for token in _chunk_text(EMPTY_RAG_MESSAGE):
                    full_response += token
                    yield _sse_json(SSEEvent(type="token", content=token))
        except Exception as exc:
            logger.error("RAG response streaming failed for session %s: %s", session_id, exc)
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        try:
            msg = await self._conv_svc.save_assistant_message(session_id, full_response)
            await self._conv_svc.auto_title_session(session_id, question)
        except Exception as exc:
            logger.error("Failed to save assistant message for session %s: %s", session_id, exc)
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        yield _sse_json(SSEEvent(type="sources", sources=[]))
        yield _sse_json(SSEEvent(type="done", message_id=str(msg.id), session_id=str(session_id)))

    def _select_mode(self, requested_mode: str) -> str:
        if settings.rag_skip_entity_extraction and requested_mode != "naive":
            return "naive"
        return requested_mode

    async def _query_with_fallback(
        self,
        question: str,
        mode: str,
        conversation_history: list[dict[str, str]],
    ) -> Any:
        result = await self._rag.aquery(
            question,
            mode=mode,
            conversation_history=conversation_history,
            stream=True,
        )

        if _is_async_iterable(result):
            return result

        answer = str(result)
        if mode != "naive" and _needs_naive_fallback(answer):
            logger.info("No context from mode=%s, retrying with mode=naive", mode)
            retry = await self._rag.aquery(
                question,
                mode="naive",
                conversation_history=conversation_history,
                stream=True,
            )
            return retry
        return answer

    async def _resolve_session_doc_scope(self, session_id: uuid.UUID) -> set[str] | None:
        """Return session-bound LightRAG doc ids for vector filtering.

        - None: no session-bound uploads, keep global retrieval.
        - set([...]): restrict retrieval to these doc ids.
        """
        attached_doc_ids = await self._conv_svc.get_attached_document_ids(session_id)
        if not attached_doc_ids:
            return None

        rag_doc_ids: set[str] = set()
        for doc_id in attached_doc_ids:
            doc = await self._doc_repo.get_by_id(doc_id)
            if doc and doc.rag_doc_id and doc.status.value == "completed":
                rag_doc_ids.add(doc.rag_doc_id)
        return rag_doc_ids


def _needs_naive_fallback(answer: str) -> bool:
    normalized = answer.lower()
    return "[no-context]" in normalized or "no context" in normalized


def _sse_json(event: SSEEvent) -> str:
    return json.dumps(event.model_dump(exclude_none=True), ensure_ascii=False)


def _chunk_text(text: str) -> list[str]:
    return [text[i : i + STREAM_CHUNK_SIZE] for i in range(0, len(text), STREAM_CHUNK_SIZE)]


def _is_async_iterable(value: Any) -> bool:
    return hasattr(value, "__aiter__")
