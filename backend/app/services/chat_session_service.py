from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.chat_session import ChatSession
from app.models.message import Message

if TYPE_CHECKING:
    from app.repositories.message_repository import MessageRepository
    from app.repositories.session_repository import SessionRepository

DEFAULT_SESSION_TITLE_PREFIX = "新對話 "


class ChatSessionService:
    """Manages conversation session CRUD operations."""

    def __init__(
        self,
        session_repo: "SessionRepository",
        message_repo: "MessageRepository",
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo

    async def create_session(
        self,
        user_id: uuid.UUID,
        query_mode: str = "hybrid",
    ) -> ChatSession:
        now = datetime.now(timezone.utc)
        title = f"{DEFAULT_SESSION_TITLE_PREFIX}{now.strftime('%Y-%m-%d %H:%M')}"
        return await self._session_repo.create({
            "user_id": user_id,
            "title": title,
            "query_mode": query_mode,
        })

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 30,
    ) -> list[ChatSession]:
        return await self._session_repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_session_with_messages(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        message_limit: int = 50,
    ) -> tuple[ChatSession, list[Message]]:
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError(f"Session not found: {session_id}")
        if session.user_id != user_id:
            raise AuthorizationError("Access denied to this session")
        messages = await self._message_repo.get_by_session(
            session_id, skip=0, limit=message_limit
        )
        return session, messages

    async def rename_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        new_title: str,
    ) -> ChatSession:
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError(f"Session not found: {session_id}")
        if session.user_id != user_id:
            raise AuthorizationError("Access denied to this session")
        return await self._session_repo.update_title(session_id, new_title)

    async def delete_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError(f"Session not found: {session_id}")
        if session.user_id != user_id:
            raise AuthorizationError("Access denied to this session")
        await self._session_repo.delete(session_id)
