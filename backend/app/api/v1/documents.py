from pathlib import Path
from uuid import UUID

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.message import MessageRole
from app.config import settings
from app.models.user import User
from app.rag.engine import RAGEngine
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.document import DocumentListResponse, DocumentStatusResponse, DocumentUploadResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(
        doc_repo=DocumentRepository(db),
        rag_engine=RAGEngine.get_rag(),
        upload_dir=Path(settings.upload_dir),
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    session_id: UUID | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(_get_document_service),
) -> DocumentUploadResponse:
    await doc_service.validate_file(file)
    stored_filename, file_path, file_size = await doc_service.save_file(file)
    doc = await doc_service.create_document_record(
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        uploader_id=current_user.id,
    )

    if session_id is not None:
        session_repo = SessionRepository(db)
        message_repo = MessageRepository(db)
        session = await session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        if session.user_id != current_user.id:
            raise AuthorizationError("Access denied to this session")

        await message_repo.create({
            "session_id": session_id,
            "role": MessageRole.system,
            "content": (
                f'[[document-upload]]{{"document_id":"{doc.id}","file_name":"{doc.original_filename}"}}'
            ),
        })
        await session_repo.increment_message_count(session_id)
        await session_repo.update_last_message(session_id, datetime.now(timezone.utc))

    await db.commit()
    background_tasks.add_task(doc_service.process_document_background, doc.id)
    return doc


@router.get("/", response_model=list[DocumentListResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(_get_document_service),
) -> list[DocumentListResponse]:
    return await doc_service.list_documents(current_user, skip=skip, limit=limit)


@router.get("/{doc_id}", response_model=DocumentListResponse)
async def get_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(_get_document_service),
) -> DocumentListResponse:
    return await doc_service.get_document(doc_id, current_user)


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(_get_document_service),
) -> DocumentStatusResponse:
    return await doc_service.get_document(doc_id, current_user)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(_get_document_service),
) -> None:
    await doc_service.delete_document(doc_id, current_user)
