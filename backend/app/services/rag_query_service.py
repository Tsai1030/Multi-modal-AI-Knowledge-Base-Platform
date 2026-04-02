import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from app.core.exceptions import NotFoundError
from app.schemas.query import SSEEvent

if TYPE_CHECKING:
    from raganything import RAGAnything

    from app.rag.llm_adapter import OllamaLLMAdapter
    from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


class RAGQueryService:
    """Integrates RAG-Anything retrieval, multi-turn context assembly, and SSE streaming.

    Query flow (DECISION STEP6 — approach B):
    1. Save user message to DB
    2. Get conversation context via ConversationService
    3. rag.aquery() retrieves knowledge-base context (non-streaming)
       → uses QueryParam(conversation_history=...) per DECISION STEP4
    4. llm_adapter.complete_stream() streams the final response with rag_result as system_prompt
    5. Save assistant message, auto_title, yield sources + done events
    """

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
        """Yield SSE-formatted JSON strings for each event in the query pipeline."""
        try:
            await self._conv_svc.save_user_message(session_id, question, mode)
        except NotFoundError as exc:
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        try:
            conv_context = await self._conv_svc.get_conversation_context(session_id, question)
            rag_result: str = await self._rag.aquery(
                question,
                mode=mode,
                conversation_history=conv_context,
            )
        except Exception as exc:
            logger.error(f"RAG query failed for session {session_id}: {exc}")
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        full_response = ""
        try:
            async for token in self._llm.complete_stream(
                question,
                system_prompt=rag_result,
            ):
                full_response += token
                yield _sse_json(SSEEvent(type="token", content=token))
        except Exception as exc:
            logger.error(f"LLM stream failed for session {session_id}: {exc}")
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        try:
            msg = await self._conv_svc.save_assistant_message(session_id, full_response)
            await self._conv_svc.auto_title_session(session_id, question)
        except Exception as exc:
            logger.error(f"Failed to save assistant message for session {session_id}: {exc}")
            yield _sse_json(SSEEvent(type="error", content=str(exc)))
            return

        yield _sse_json(SSEEvent(type="sources", sources=[]))
        yield _sse_json(SSEEvent(type="done", message_id=str(msg.id), session_id=str(session_id)))


def _sse_json(event: SSEEvent) -> str:
    return json.dumps(event.model_dump(exclude_none=True), ensure_ascii=False)
