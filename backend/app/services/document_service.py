import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from lightrag.base import DocStatus

from app.core.exceptions import AppValidationError, AuthorizationError, NotFoundError
from app.db.session import AsyncSessionFactory
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

# NOTE/TODO: process_document_background uses AsyncSessionFactory from app.db.session
# to create an independent DB session (request session is closed by the time the task runs).
# Docker-stage integration tests should replace the mock with real service calls.


class DocumentService:
    """Manages document CRUD, local file storage, and RAG-Anything processing."""

    ALLOWED_EXTENSIONS: frozenset = frozenset({
        ".pdf", ".docx", ".doc", ".pptx", ".ppt",
        ".xlsx", ".xls", ".md", ".txt", ".jpg", ".jpeg", ".png",
    })
    MAX_FILE_SIZE_MB: int = 50
    PROCESS_TIMEOUT_SECONDS: int = 600

    def __init__(self, doc_repo: DocumentRepository, rag_engine, upload_dir: Path) -> None:
        self._doc_repo = doc_repo
        self._rag = rag_engine
        self._upload_dir = upload_dir.resolve()

    async def validate_file(self, file: UploadFile) -> None:
        """Validate file extension and size. Raises AppValidationError on failure."""
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise AppValidationError(f"File type '{ext}' is not allowed")

        content = await file.read()
        await file.seek(0)

        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            raise AppValidationError(f"File size {size_mb:.1f} MB exceeds limit of {self.MAX_FILE_SIZE_MB} MB")

    async def save_file(self, file: UploadFile) -> tuple[str, str, int]:
        """Save uploaded file to upload_dir/{uuid}{ext}. Returns (stored_filename, file_path, file_size)."""
        filename = file.filename or "unknown"
        ext = Path(filename).suffix.lower()
        stored_filename = f"{uuid.uuid4()}{ext}"
        file_path = (self._upload_dir / stored_filename).resolve()

        self._upload_dir.mkdir(parents=True, exist_ok=True)

        content = await file.read()
        file_path.write_bytes(content)

        return stored_filename, str(file_path), len(content)

    async def create_document_record(
        self,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        uploader_id: uuid.UUID,
    ) -> Document:
        """Insert a Document record with status=pending."""
        title = Path(original_filename).stem
        return await self._doc_repo.create({
            "title": title,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": mime_type or "application/octet-stream",
            "status": DocumentStatus.pending,
            "uploaded_by_id": uploader_id,
        })

    async def process_document_background(self, document_id: uuid.UUID) -> None:
        """Background task: parse document via RAG-Anything and update DB status.

        Creates its own AsyncSession because the request session is already closed
        by the time this task runs.
        """
        logger.info("Background processing started for document %s", document_id)
        async with AsyncSessionFactory() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get_by_id(document_id)
            if doc is None:
                logger.error(f"Background task: document {document_id} not found")
                return

            await doc_repo.update_status(document_id, DocumentStatus.processing)
            await session.commit()
            logger.info(
                "Document %s marked as processing (file=%s, path=%s)",
                document_id,
                doc.original_filename,
                doc.file_path,
            )

            rag_doc_id = str(uuid.uuid4())
            try:
                document_path = Path(doc.file_path)
                if not document_path.is_absolute():
                    document_path = document_path.resolve()

                if not document_path.exists():
                    fallback_path = (self._upload_dir / doc.stored_filename).resolve()
                    logger.warning(
                        "Document %s file path %s not found, trying fallback path %s",
                        document_id,
                        document_path,
                        fallback_path,
                    )
                    document_path = fallback_path

                if not document_path.exists():
                    raise FileNotFoundError(
                        f"Uploaded file not found for document {document_id}: {document_path}"
                    )

                if str(document_path) != doc.file_path:
                    await doc_repo.update(document_id, {"file_path": str(document_path)})
                    await session.commit()
                    logger.info(
                        "Document %s file_path normalized to %s",
                        document_id,
                        document_path,
                    )

                output_dir = document_path.parent / "output"
                output_dir.mkdir(parents=True, exist_ok=True)
                await self._cleanup_stale_lightrag_queue()
                logger.info(
                    "Document %s entering RAG processing (rag_doc_id=%s, output_dir=%s)",
                    document_id,
                    rag_doc_id,
                    output_dir,
                )

                result = await asyncio.wait_for(
                    self._rag.process_document_complete(
                        file_path=str(document_path),
                        output_dir=str(output_dir),
                        doc_id=rag_doc_id,
                    ),
                    timeout=self.PROCESS_TIMEOUT_SECONDS,
                )
                logger.info(
                    "Document %s finished RAG processing call with result=%s",
                    document_id,
                    result,
                )

                lightrag_status = await self._rag.lightrag.doc_status.get_by_id(rag_doc_id)
                status_value = None
                error_message = None
                if isinstance(lightrag_status, dict):
                    raw_status = lightrag_status.get("status")
                    status_value = raw_status.value if hasattr(raw_status, "value") else raw_status
                    error_message = lightrag_status.get("error_msg")

                if status_value != DocStatus.PROCESSED.value:
                    raise RuntimeError(
                        error_message
                        or f"LightRAG indexing did not complete successfully (status={status_value})"
                    )

                await doc_repo.update(document_id, {
                    "status": DocumentStatus.completed,
                    "rag_doc_id": rag_doc_id,
                    "error_message": None,
                })
                await session.commit()
                logger.info(f"Document {document_id} processed successfully (rag_doc_id={rag_doc_id})")

            except TimeoutError:
                logger.exception(
                    "Document %s processing timed out after %s seconds",
                    document_id,
                    self.PROCESS_TIMEOUT_SECONDS,
                )
                await doc_repo.update_status(
                    document_id,
                    DocumentStatus.failed,
                    error=f"Processing timed out after {self.PROCESS_TIMEOUT_SECONDS} seconds",
                )
                await session.commit()
            except Exception as exc:
                logger.exception("Document %s processing failed", document_id)
                await doc_repo.update_status(document_id, DocumentStatus.failed, error=str(exc))
                await session.commit()

    async def _cleanup_stale_lightrag_queue(self) -> None:
        stale_statuses = (DocStatus.PENDING, DocStatus.PROCESSING, DocStatus.FAILED)
        stale_doc_ids: set[str] = set()
        stale_chunk_ids: set[str] = set()

        for status in stale_statuses:
            docs = await self._rag.lightrag.doc_status.get_docs_by_status(status)
            for doc_id, status_doc in docs.items():
                stale_doc_ids.add(doc_id)
                if getattr(status_doc, "chunks_list", None):
                    stale_chunk_ids.update(status_doc.chunks_list)

        if not stale_doc_ids and not stale_chunk_ids:
            return

        logger.info(
            "Cleaning stale LightRAG queue before indexing: %s docs, %s chunks",
            len(stale_doc_ids),
            len(stale_chunk_ids),
        )

        if stale_chunk_ids:
            await self._rag.lightrag.text_chunks.delete(list(stale_chunk_ids))
            await self._rag.lightrag.text_chunks.index_done_callback()
            await self._rag.lightrag.chunks_vdb.delete(list(stale_chunk_ids))
            await self._rag.lightrag.chunks_vdb.index_done_callback()

        if stale_doc_ids:
            await self._rag.lightrag.full_docs.delete(list(stale_doc_ids))
            await self._rag.lightrag.full_docs.index_done_callback()
            await self._rag.lightrag.doc_status.delete(list(stale_doc_ids))
            await self._rag.lightrag.doc_status.index_done_callback()

    async def list_documents(self, user: User, skip: int = 0, limit: int = 50) -> list[Document]:
        """Admin sees all documents; regular users see only their own."""
        if user.role == UserRole.admin:
            return await self._doc_repo.get_all(skip=skip, limit=limit)
        return await self._doc_repo.get_by_uploader(user.id, skip=skip, limit=limit)

    async def get_document(self, doc_id: uuid.UUID, user: User) -> Document:
        """Fetch a single document, enforcing ownership for non-admin users."""
        doc = await self._doc_repo.get_by_id(doc_id)
        if doc is None:
            raise NotFoundError(f"Document {doc_id} not found")
        if user.role != UserRole.admin and doc.uploaded_by_id != user.id:
            raise AuthorizationError("Access denied")
        return doc

    async def delete_document(self, doc_id: uuid.UUID, user: User) -> None:
        """Delete vectors, local file, and DB record."""
        doc = await self.get_document(doc_id, user)

        if doc.rag_doc_id:
            try:
                await self._rag.lightrag.adelete_by_doc_id(doc.rag_doc_id)
            except Exception as exc:
                logger.error(f"Failed to delete vectors for document {doc_id}: {exc}")

        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()

        await self._doc_repo.delete(doc_id)
