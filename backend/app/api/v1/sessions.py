from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.message import MessageResponse, SessionDetailResponse
from app.schemas.session import (
    SessionCreateRequest,
    SessionListResponse,
    SessionRenameRequest,
    SessionResponse,
)
from app.services.chat_session_service import ChatSessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_chat_session_service(db: AsyncSession = Depends(get_db)) -> ChatSessionService:
    return ChatSessionService(
        session_repo=SessionRepository(db),
        message_repo=MessageRepository(db),
    )


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    svc: ChatSessionService = Depends(_get_chat_session_service),
) -> SessionResponse:
    session = await svc.create_session(current_user.id, query_mode=body.query_mode)
    return session


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    skip: int = 0,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    svc: ChatSessionService = Depends(_get_chat_session_service),
) -> SessionListResponse:
    sessions = await svc.list_sessions(current_user.id, skip=skip, limit=limit)
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ChatSessionService = Depends(_get_chat_session_service),
) -> SessionDetailResponse:
    session, messages = await svc.get_session_with_messages(session_id, current_user.id)
    return SessionDetailResponse(
        session=session,
        messages=[MessageResponse.from_orm_message(m) for m in messages],
    )


@router.patch("/{session_id}/title", response_model=SessionResponse)
async def rename_session(
    session_id: UUID,
    body: SessionRenameRequest,
    current_user: User = Depends(get_current_user),
    svc: ChatSessionService = Depends(_get_chat_session_service),
) -> SessionResponse:
    session = await svc.rename_session(session_id, current_user.id, body.title)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ChatSessionService = Depends(_get_chat_session_service),
) -> None:
    await svc.delete_session(session_id, current_user.id)
