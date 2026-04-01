import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatSession
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[ChatSession]):
    """Repository for ChatSession model CRUD and domain-specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatSession)

    async def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 30
    ) -> list[ChatSession]:
        result = await self._session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.last_message_at.desc().nulls_last(), ChatSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_title(self, session_id: uuid.UUID, title: str) -> ChatSession | None:
        return await self.update(session_id, {"title": title})

    async def update_last_message(self, session_id: uuid.UUID, ts: datetime) -> None:
        await self.update(session_id, {"last_message_at": ts})

    async def increment_message_count(self, session_id: uuid.UUID) -> None:
        instance = await self.get_by_id(session_id)
        if instance is not None:
            await self.update(session_id, {"message_count": instance.message_count + 1})

    async def update_compact_data(
        self, session_id: uuid.UUID, summary: str, is_compacted: bool
    ) -> ChatSession | None:
        return await self.update(
            session_id, {"compact_summary": summary, "is_compacted": is_compacted}
        )
