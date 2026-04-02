import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.core.exceptions import NotFoundError
from app.models.user import User, UserRole
from app.rag.engine import RAGEngine
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RoleUpdateRequest, StatusUpdateRequest, UserPublicResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


@router.get("/users", response_model=list[UserPublicResponse])
async def list_users(
    user_repo: UserRepository = Depends(_get_user_repo),
    _: User = Depends(get_current_admin),
) -> list[User]:
    return await user_repo.get_all(limit=500)


@router.patch("/users/{user_id}/role", response_model=UserPublicResponse)
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    user_repo: UserRepository = Depends(_get_user_repo),
    _: User = Depends(get_current_admin),
) -> User:
    if body.role not in (r.value for r in UserRole):
        from app.core.exceptions import AppValidationError
        raise AppValidationError(f"Invalid role: {body.role}")
    updated = await user_repo.update(user_id, {"role": body.role})
    if updated is None:
        raise NotFoundError(f"User not found: {user_id}")
    return updated


@router.patch("/users/{user_id}/status", response_model=UserPublicResponse)
async def update_user_status(
    user_id: uuid.UUID,
    body: StatusUpdateRequest,
    user_repo: UserRepository = Depends(_get_user_repo),
    _: User = Depends(get_current_admin),
) -> User:
    updated = await user_repo.update(user_id, {"is_active": body.is_active})
    if updated is None:
        raise NotFoundError(f"User not found: {user_id}")
    return updated


@router.delete("/vectors/orphaned", status_code=status.HTTP_200_OK)
async def purge_orphaned_vectors(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    """Delete ChromaDB chunk vectors that no longer have a matching document record."""
    rag = RAGEngine.get_rag()
    doc_repo = DocumentRepository(db)

    active_docs = await doc_repo.get_all(limit=10000)
    active_rag_ids = {doc.rag_doc_id for doc in active_docs if doc.rag_doc_id}

    collection = getattr(rag.lightrag.chunks_vdb, "_collection", None)
    if collection is None:
        return {"deleted": 0, "message": "ChromaDB collection not available"}

    all_chunks = await collection.get(include=["metadatas"])
    if not all_chunks["ids"]:
        return {"deleted": 0, "message": "No chunks in vector store"}

    orphaned_ids = [
        chunk_id
        for chunk_id, meta in zip(all_chunks["ids"], all_chunks["metadatas"])
        if meta.get("full_doc_id") not in active_rag_ids
    ]

    if orphaned_ids:
        await collection.delete(ids=orphaned_ids)

    return {"deleted": len(orphaned_ids), "message": f"Deleted {len(orphaned_ids)} orphaned chunks"}
