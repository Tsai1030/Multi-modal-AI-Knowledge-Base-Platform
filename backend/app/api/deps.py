from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import SecurityService
from app.db.session import get_async_session
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = SecurityService.decode_token(token)
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_str(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.admin:
        raise AuthorizationError("Admin access required")
    return current_user
