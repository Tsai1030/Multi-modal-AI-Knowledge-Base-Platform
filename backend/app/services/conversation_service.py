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

DEFAULT_SESSION_TITLE_PREFIX = "新對話 "
DOCUMENT_UPLOAD_PREFIX = "[[document-upload]]"
SYSTEM_CONTENT = (
    "你是 RAG 知識庫助理。回答時優先根據已檢索到的文件內容作答，"
    "若資料不足請明確說明不知道，不要假裝讀過不存在的內容。"
)


class ConversationService:
    """Manages multi-turn conversation state for a single session."""

    def __init__(
        self,
        session_repo: "SessionRepository",
        message_repo: "MessageRepository",
        compactor: "ConversationCompactor",
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._compactor = compactor

    async def get_conversation_context(
        self,
        session_id: uuid.UUID,
        current_question: str,
    ) -> list[dict]:
        """Assemble conversation history for injection into RAG-Anything."""
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError(f"Session not found: {session_id}")

        messages = await self._message_repo.get_recent_by_session(
            session_id, self._compactor.compact_threshold
        )

        summary: str | None = session.compact_summary
        if self._compactor.should_compact(session.message_count):
            summary = await self._execute_compact(session_id, messages)
            messages = await self._message_repo.get_recent_by_session(
                session_id, self._compactor.compact_target + 1
            )

        history: list[dict] = [{"role": "system", "content": SYSTEM_CONTENT}]
        if summary:
            history.append({"role": "assistant", "content": summary})

        for msg in messages:
            if msg.is_compacted_summary:
                continue
            if msg.role == MessageRole.system and msg.content.startswith(DOCUMENT_UPLOAD_PREFIX):
                continue
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
        session = await self._session_repo.get_by_id(session_id)
        if session is None or not session.title.startswith(DEFAULT_SESSION_TITLE_PREFIX):
            return
        await self._session_repo.update_title(session_id, first_user_message[:20])

    async def get_attached_document_ids(self, session_id: uuid.UUID) -> list[uuid.UUID]:
        """Parse [[document-upload]] system messages in this session and return unique document ids."""
        messages = await self._message_repo.get_by_session(session_id, skip=0, limit=500)
        unique_doc_ids: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()

        for msg in messages:
            if msg.role != MessageRole.system:
                continue
            content = msg.content or ""
            if not content.startswith(DOCUMENT_UPLOAD_PREFIX):
                continue

            payload_raw = content[len(DOCUMENT_UPLOAD_PREFIX):]
            try:
                payload = json.loads(payload_raw)
                doc_id_raw = payload.get("document_id")
                if not doc_id_raw:
                    continue
                doc_id = uuid.UUID(str(doc_id_raw))
            except Exception:
                continue

            if doc_id in seen:
                continue
            seen.add(doc_id)
            unique_doc_ids.append(doc_id)

        return unique_doc_ids
