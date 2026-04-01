import uuid

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import SecurityService
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


class AuthService:
    """Handles user registration, authentication, and lookup."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def register(self, email: str, password: str, full_name: str) -> User:
        existing = await self._user_repo.get_by_email(email)
        if existing is not None:
            raise ConflictError(f"Email already registered: {email}")
        hashed = SecurityService.hash_password(password)
        return await self._user_repo.create({
            "email": email,
            "hashed_password": hashed,
            "full_name": full_name,
            "role": UserRole.user,
            "is_active": True,
        })

    async def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = await self._user_repo.get_by_email(email)
        if user is None or not SecurityService.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        token = SecurityService.create_access_token(subject=str(user.id), role=user.role.value)
        return user, token

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User not found: {user_id}")
        return user
