import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from app.config import settings
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
    ) -> None:
        self._rag = rag_engine
        self._llm = llm_adapter
        self._conv_svc = conversation_service

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


def _needs_naive_fallback(answer: str) -> bool:
    normalized = answer.lower()
    return "[no-context]" in normalized or "no context" in normalized


def _sse_json(event: SSEEvent) -> str:
    return json.dumps(event.model_dump(exclude_none=True), ensure_ascii=False)


def _chunk_text(text: str) -> list[str]:
    return [text[i : i + STREAM_CHUNK_SIZE] for i in range(0, len(text), STREAM_CHUNK_SIZE)]


def _is_async_iterable(value: Any) -> bool:
    return hasattr(value, "__aiter__")
