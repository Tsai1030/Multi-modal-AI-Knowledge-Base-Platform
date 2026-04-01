from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.exceptions import NotFoundError
from app.models.message import Message, MessageRole

if TYPE_CHECKING:
    from app.rag.conversation_compactor import ConversationCompactor
    from app.repositories.message_repository import MessageRepository
    from app.repositories.session_repository import SessionRepository

_SYSTEM_CONTENT = (
    "你是一個知識庫助理，請根據提供的對話歷史和知識庫內容，準確、有條理地回答用戶的問題。"
)


class ConversationService:
    """Manages multi-turn conversation state for a single session.

    Responsibilities: context assembly, compact triggering, message persistence.

    NOTE: rag.aquery() must receive this context via conversation_history= parameter
    (NOT history_messages=). See STEP 3 decision log.
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        message_repo: MessageRepository,
        compactor: ConversationCompactor,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._compactor = compactor

    async def get_conversation_context(
        self,
        session_id: uuid.UUID,
        current_question: str,
    ) -> list[dict]:
        """Assemble conversation history for injection into RAG-Anything.

        Returns a list of {role, content} dicts to be passed as:
            await rag.aquery(query, param=QueryParam(conversation_history=context))

        Flow:
        1. Fetch recent messages (up to compact_threshold) from DB
        2. Compact if session.message_count >= threshold
        3. Assemble [system, summary(optional), ...history, current_question]
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError(f"Session not found: {session_id}")

        messages = await self._message_repo.get_recent_by_session(
            session_id, self._compactor.compact_threshold
        )

        summary: str | None = session.compact_summary
        if self._compactor.should_compact(session.message_count):
            summary = await self._execute_compact(session_id, messages)
            # Fetch compact_target+1 to account for the summary marker inserted in DB.
            # The marker (is_compacted_summary=True) is filtered during context assembly.
            messages = await self._message_repo.get_recent_by_session(
                session_id, self._compactor.compact_target + 1
            )

        history: list[dict] = [{"role": "system", "content": _SYSTEM_CONTENT}]
        if summary:
            history.append({"role": "assistant", "content": summary})

        for msg in messages:
            if not msg.is_compacted_summary:
                history.append({"role": msg.role.value, "content": msg.content})

        history.append({"role": "user", "content": current_question})
        return history

    async def save_user_message(
        self,
        session_id: uuid.UUID,
        content: str,
        query_mode: str,
    ) -> Message:
        token_count = self._compactor.estimate_tokens(content)
        msg = await self._message_repo.create({
            "session_id": session_id,
            "role": MessageRole.user,
            "content": content,
            "token_count": token_count,
            "query_mode": query_mode,
        })
        await self._session_repo.increment_message_count(session_id)
        return msg

    async def save_assistant_message(
        self,
        session_id: uuid.UUID,
        content: str,
        rag_sources: list[str] | None = None,
    ) -> Message:
        token_count = self._compactor.estimate_tokens(content)
        rag_sources_str = json.dumps(rag_sources, ensure_ascii=False) if rag_sources else None
        msg = await self._message_repo.create({
            "session_id": session_id,
            "role": MessageRole.assistant,
            "content": content,
            "token_count": token_count,
            "rag_sources": rag_sources_str,
        })
        now = datetime.now(timezone.utc)
        await self._session_repo.update_last_message(session_id, now)
        await self._session_repo.increment_message_count(session_id)
        return msg

    async def _execute_compact(
        self,
        session_id: uuid.UUID,
        messages: list[Message],
    ) -> str:
        """Compress old messages and persist the summary.

        Steps:
        1. Summarise old messages via LLM (keeps most recent compact_target msgs)
        2. Delete compressed messages from DB
        3. Insert a summary marker message (role=system, is_compacted_summary=True)
        4. Update session.compact_summary and is_compacted
        """
        summary, msgs_to_keep = await self._compactor.compact(
            messages, keep_last_n=self._compactor.compact_target
        )

        keep_ids = {msg.id for msg in msgs_to_keep}
        for msg in messages:
            if msg.id not in keep_ids:
                await self._message_repo.delete(msg.id)

        await self._message_repo.create({
            "session_id": session_id,
            "role": MessageRole.system,
            "content": summary,
            "is_compacted_summary": True,
        })
        await self._session_repo.update_compact_data(
            session_id, summary=summary, is_compacted=True
        )
        return summary

    async def auto_title_session(
        self,
        session_id: uuid.UUID,
        first_user_message: str,
    ) -> None:
        """Set session title from first 20 chars of first user message if still default."""
        session = await self._session_repo.get_by_id(session_id)
        if session is None or not session.title.startswith("新對話"):
            return
        await self._session_repo.update_title(session_id, first_user_message[:20])
