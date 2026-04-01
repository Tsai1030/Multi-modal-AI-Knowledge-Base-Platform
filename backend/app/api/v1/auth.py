from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserCreateRequest, UserLoginRequest, UserPublicResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/signup", response_model=UserPublicResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: UserCreateRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> User:
    return await auth_service.register(
        email=body.email, password=body.password, full_name=body.full_name
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLoginRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    _, token = await auth_service.authenticate(email=body.email, password=body.password)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout() -> dict:
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserPublicResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
