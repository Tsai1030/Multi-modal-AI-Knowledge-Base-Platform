"""
Tests for document upload, status query, and delete endpoints.

NOTE/TODO: All tests use a mocked RAG engine and a no-op process_document_background.
Docker-stage integration tests should replace mocks with real service calls.
"""
import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.api.v1.documents import _get_document_service
from app.db.base import Base
from app.main import app
from app.models.document import DocumentStatus
from app.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService

pytestmark = pytest.mark.asyncio(loop_scope="function")

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
UPLOAD_URL = "/api/v1/documents/upload"
LIST_URL = "/api/v1/documents/"

VALID_USER = {"email": "uploader@example.com", "password": "Password1", "full_name": "Uploader"}
OTHER_USER = {"email": "other@example.com", "password": "Password1", "full_name": "Other"}
ADMIN_USER = {"email": "admin@example.com", "password": "Admin123!", "full_name": "Admin"}


def _make_pdf_bytes(size_bytes: int = 1024) -> bytes:
    return b"%PDF-1.4 fake " + b"x" * max(0, size_bytes - 14)


def _pdf_file(name: str = "test.pdf", size_bytes: int = 1024):
    return ("file", (name, io.BytesIO(_make_pdf_bytes(size_bytes)), "application/pdf"))


def _make_mock_rag() -> MagicMock:
    mock_rag = MagicMock()
    mock_rag.lightrag = MagicMock()
    mock_rag.lightrag.adelete_by_doc_id = AsyncMock()
    return mock_rag


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(loop_scope="function")
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(loop_scope="function")
async def doc_client(db_session: AsyncSession, tmp_path: Path):
    """AsyncClient with mocked RAG engine and no-op process_document_background.

    NOTE/TODO: Docker-stage tests should replace mocks with real service calls.
    """
    mock_rag = _make_mock_rag()

    async def override_get_db():
        yield db_session

    def override_doc_service():
        return DocumentService(
            doc_repo=DocumentRepository(db_session),
            rag_engine=mock_rag,
            upload_dir=tmp_path / "uploads",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[_get_document_service] = override_doc_service

    # Patch background task at class level so every service instance uses the no-op
    with patch.object(DocumentService, "process_document_background", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, mock_rag

    app.dependency_overrides.clear()


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    await client.post(SIGNUP_URL, json=payload)
    resp = await client.post(LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    return resp.json()["access_token"]


# ── Upload ────────────────────────────────────────────────────────────────────

async def test_upload_pdf_success(doc_client):
    client, _ = doc_client
    token = await _register_and_login(client, VALID_USER)
    resp = await client.post(
        UPLOAD_URL,
        files=[_pdf_file()],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == DocumentStatus.pending
    assert body["title"] == "test"
    assert "id" in body


async def test_upload_disallowed_extension_returns_422(doc_client):
    client, _ = doc_client
    token = await _register_and_login(client, VALID_USER)
    resp = await client.post(
        UPLOAD_URL,
        files=[("file", ("malware.exe", io.BytesIO(b"binary"), "application/octet-stream"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_upload_exceeds_size_limit_returns_422(doc_client):
    client, _ = doc_client
    over_limit = (DocumentService.MAX_FILE_SIZE_MB * 1024 * 1024) + 1
    token = await _register_and_login(client, VALID_USER)
    resp = await client.post(
        UPLOAD_URL,
        files=[_pdf_file(size_bytes=over_limit)],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_upload_without_token_returns_401(doc_client):
    client, _ = doc_client
    resp = await client.post(UPLOAD_URL, files=[_pdf_file()])
    assert resp.status_code == 401


# ── Status query ──────────────────────────────────────────────────────────────

async def test_status_pending_after_upload(doc_client):
    client, _ = doc_client
    token = await _register_and_login(client, VALID_USER)
    upload_resp = await client.post(
        UPLOAD_URL,
        files=[_pdf_file()],
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = upload_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/documents/{doc_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == DocumentStatus.pending


async def test_status_transitions(doc_client, db_session: AsyncSession):
    """Verify the status endpoint reflects each DocumentStatus value correctly."""
    client, _ = doc_client
    token = await _register_and_login(client, VALID_USER)
    upload_resp = await client.post(
        UPLOAD_URL,
        files=[_pdf_file()],
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = upload_resp.json()["id"]
    doc_repo = DocumentRepository(db_session)

    for target_status in (DocumentStatus.processing, DocumentStatus.completed):
        await doc_repo.update_status(uuid.UUID(doc_id), target_status)
        resp = await client.get(
            f"/api/v1/documents/{doc_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == target_status


async def test_status_nonexistent_doc_returns_404(doc_client):
    client, _ = doc_client
    token = await _register_and_login(client, VALID_USER)
    resp = await client.get(
        f"/api/v1/documents/{uuid.uuid4()}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── List & detail ─────────────────────────────────────────────────────────────

async def test_list_documents_returns_own_only(doc_client):
    client, _ = doc_client
    token_a = await _register_and_login(client, VALID_USER)
    token_b = await _register_and_login(client, OTHER_USER)

    await client.post(UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token_a}"})
    await client.post(UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token_a}"})
    await client.post(UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token_b}"})

    resp = await client.get(LIST_URL, headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_document_other_user_returns_403(doc_client):
    client, _ = doc_client
    token_a = await _register_and_login(client, VALID_USER)
    token_b = await _register_and_login(client, OTHER_USER)

    upload_resp = await client.post(
        UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token_a}"}
    )
    doc_id = upload_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_by_owner_returns_204(doc_client):
    client, _ = doc_client
    token = await _register_and_login(client, VALID_USER)
    upload_resp = await client.post(
        UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token}"}
    )
    doc_id = upload_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 404


async def test_delete_by_other_user_returns_403(doc_client):
    client, _ = doc_client
    token_a = await _register_and_login(client, VALID_USER)
    token_b = await _register_and_login(client, OTHER_USER)

    upload_resp = await client.post(
        UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token_a}"}
    )
    doc_id = upload_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


async def test_delete_by_admin_returns_204(doc_client, db_session: AsyncSession):
    """Admin can delete any user's document."""
    client, _ = doc_client
    token_user = await _register_and_login(client, VALID_USER)
    upload_resp = await client.post(
        UPLOAD_URL, files=[_pdf_file()], headers={"Authorization": f"Bearer {token_user}"}
    )
    doc_id = upload_resp.json()["id"]

    # Register admin and elevate role directly in the test DB
    await client.post(SIGNUP_URL, json=ADMIN_USER)
    await db_session.execute(
        update(User).where(User.email == ADMIN_USER["email"]).values(role=UserRole.admin)
    )
    token_admin = await _register_and_login(client, ADMIN_USER)

    resp = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp.status_code == 204


# ── Background task unit tests ─────────────────────────────────────────────────

async def test_process_document_background_success(tmp_path: Path):
    """Unit test: background task updates status and stores rag_doc_id on success.

    NOTE/TODO: Docker-stage tests should replace mocks with real RAG engine and DB.
    """
    doc_id = uuid.uuid4()
    fake_file = tmp_path / "test.pdf"
    fake_file.write_bytes(b"%PDF fake")

    mock_doc = MagicMock()
    mock_doc.file_path = str(fake_file)

    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
    mock_repo.update_status = AsyncMock()
    mock_repo.update = AsyncMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_rag = MagicMock()
    mock_rag.process_document_complete = AsyncMock(return_value=None)

    with (
        patch("app.services.document_service.AsyncSessionFactory", return_value=mock_session),
        patch("app.services.document_service.DocumentRepository", return_value=mock_repo),
    ):
        svc = DocumentService(doc_repo=AsyncMock(), rag_engine=mock_rag, upload_dir=tmp_path)
        await svc.process_document_background(doc_id)

    mock_repo.update_status.assert_called_once_with(doc_id, DocumentStatus.processing)
    mock_rag.process_document_complete.assert_called_once()
    call_kwargs = mock_rag.process_document_complete.call_args.kwargs
    assert call_kwargs["file_path"] == str(fake_file)
    assert "doc_id" in call_kwargs

    update_args = mock_repo.update.call_args[0]
    assert update_args[1]["status"] == DocumentStatus.completed
    assert "rag_doc_id" in update_args[1]


async def test_process_document_background_failure(tmp_path: Path):
    """Unit test: background task sets status=failed when RAG raises an exception."""
    doc_id = uuid.uuid4()
    fake_file = tmp_path / "test.pdf"
    fake_file.write_bytes(b"%PDF fake")

    mock_doc = MagicMock()
    mock_doc.file_path = str(fake_file)

    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
    mock_repo.update_status = AsyncMock()
    mock_repo.update = AsyncMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_rag = MagicMock()
    mock_rag.process_document_complete = AsyncMock(side_effect=RuntimeError("parse error"))

    with (
        patch("app.services.document_service.AsyncSessionFactory", return_value=mock_session),
        patch("app.services.document_service.DocumentRepository", return_value=mock_repo),
    ):
        svc = DocumentService(doc_repo=AsyncMock(), rag_engine=mock_rag, upload_dir=tmp_path)
        await svc.process_document_background(doc_id)

    last_status_call = mock_repo.update_status.call_args_list[-1]
    assert last_status_call[0][1] == DocumentStatus.failed
