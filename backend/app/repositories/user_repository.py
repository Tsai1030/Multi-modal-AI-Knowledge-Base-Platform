import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model CRUD and domain-specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self) -> list[User]:
        result = await self._session.execute(
            select(User).where(User.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_by_id_str(self, id_str: str) -> User | None:
        try:
            return await self.get_by_id(uuid.UUID(id_str))
        except ValueError:
            return None

    async def deactivate(self, id: uuid.UUID) -> User | None:
        return await self.update(id, {"is_active": False})
