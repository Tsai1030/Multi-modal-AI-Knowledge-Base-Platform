import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for Message model CRUD and domain-specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Message)

    async def get_by_session(
        self, session_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_by_session(self, session_id: uuid.UUID, n: int) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(n)
        )
        rows = list(result.scalars().all())
        return list(reversed(rows))

    async def get_session_token_total(self, session_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(Message.token_count), 0)).where(
                Message.session_id == session_id
            )
        )
        return result.scalar_one()

    async def delete_by_session(self, session_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(Message).where(Message.session_id == session_id)
        )
        messages = list(result.scalars().all())
        for msg in messages:
            await self._session.delete(msg)
        await self._session.flush()
        return len(messages)

    async def bulk_create(self, messages: list[dict]) -> list[Message]:
        instances = [Message(**data) for data in messages]
        self._session.add_all(instances)
        await self._session.flush()
        for instance in instances:
            await self._session.refresh(instance)
        return instances
