import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document model CRUD and domain-specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_by_uploader(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.uploaded_by_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[Document]:
        result = await self._session.execute(
            select(Document).where(Document.status == status)
        )
        return list(result.scalars().all())

    async def update_status(
        self, doc_id: uuid.UUID, status: str, error: str | None = None
    ) -> Document | None:
        data: dict = {"status": status}
        if error is not None:
            data["error_message"] = error
        return await self.update(doc_id, data)

    async def get_by_rag_doc_id(self, rag_doc_id: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.rag_doc_id == rag_doc_id)
        )
        return result.scalar_one_or_none()
