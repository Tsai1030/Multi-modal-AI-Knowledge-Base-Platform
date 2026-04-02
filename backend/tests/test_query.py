"""
Tests for the SSE streaming query endpoint.

Strategy:
- Session CRUD uses a real in-memory SQLite DB (same as test_sessions.py).
- RAG engine and LLM adapter are mocked to avoid requiring running services.
- _get_rag_query_service is overridden to inject real ConversationService (with test DB)
  and mocked RAG/LLM, so DB message persistence is exercised end-to-end.

NOTE/TODO: Docker-stage integration tests should replace mocks with real RAG/LLM calls.
"""
import json
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.api.v1.query import _get_rag_query_service
from app.db.base import Base
from app.main import app
from app.rag.conversation_compactor import ConversationCompactor
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.services.conversation_service import ConversationService
from app.services.rag_query_service import RAGQueryService

pytestmark = pytest.mark.asyncio(loop_scope="function")

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
SESSIONS_URL = "/api/v1/sessions/"
QUERY_URL = "/api/v1/query/stream"

VALID_USER = {"email": "quser@example.com", "password": "Password1", "full_name": "Query User"}

_MOCK_RAG_RESPONSE = "這是來自知識庫的相關內容。"
_MOCK_LLM_TOKENS = ["Hello", " ", "World", "!"]


def _make_mock_llm(tokens: list[str] = _MOCK_LLM_TOKENS) -> MagicMock:
    mock_llm = MagicMock()

    async def _stream(*args, **kwargs) -> AsyncGenerator[str, None]:
        for token in tokens:
            yield token

    mock_llm.complete_stream = _stream
    mock_llm.complete = AsyncMock(return_value="summary")
    return mock_llm


def _make_mock_rag(response: str = _MOCK_RAG_RESPONSE) -> MagicMock:
    mock_rag = MagicMock()
    mock_rag.aquery = AsyncMock(return_value=response)
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
async def query_client(db_session: AsyncSession):
    """AsyncClient with mocked RAG/LLM and real ConversationService using test DB."""
    mock_rag = _make_mock_rag()
    mock_llm = _make_mock_llm()

    async def override_get_db():
        yield db_session

    def override_rag_query_service():
        compactor = ConversationCompactor(llm_adapter=mock_llm)
        conv_svc = ConversationService(
            session_repo=SessionRepository(db_session),
            message_repo=MessageRepository(db_session),
            compactor=compactor,
        )
        return RAGQueryService(
            rag_engine=mock_rag,
            llm_adapter=mock_llm,
            conversation_service=conv_svc,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[_get_rag_query_service] = override_rag_query_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, mock_rag, mock_llm

    app.dependency_overrides.clear()


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    await client.post(SIGNUP_URL, json=payload)
    resp = await client.post(LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    return resp.json()["access_token"]


async def _create_session(client: AsyncClient, token: str) -> str:
    resp = await client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


# ── Auth guards ───────────────────────────────────────────────────────────────

async def test_query_stream_without_token_returns_401(query_client):
    client, _, _ = query_client
    resp = await client.post(QUERY_URL, json={"session_id": str(uuid.uuid4()), "question": "hi"})
    assert resp.status_code == 401


async def test_query_stream_nonexistent_session_returns_404(query_client):
    client, _, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    resp = await client.post(
        QUERY_URL,
        json={"session_id": str(uuid.uuid4()), "question": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── SSE format ────────────────────────────────────────────────────────────────

async def test_query_stream_returns_event_stream_content_type(query_client):
    client, _, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    session_id = await _create_session(client, token)

    resp = await client.post(
        QUERY_URL,
        json={"session_id": session_id, "question": "test question"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


async def test_query_stream_emits_token_events(query_client):
    client, _, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    session_id = await _create_session(client, token)

    resp = await client.post(
        QUERY_URL,
        json={"session_id": session_id, "question": "test question"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    lines = [ln for ln in resp.text.splitlines() if ln.startswith("data: ") and ln != "data: [DONE]"]
    events = [json.loads(ln[6:]) for ln in lines]
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == len(_MOCK_LLM_TOKENS)
    assert "".join(e["content"] for e in token_events) == "".join(_MOCK_LLM_TOKENS)


async def test_query_stream_ends_with_done_sentinel(query_client):
    client, _, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    session_id = await _create_session(client, token)

    resp = await client.post(
        QUERY_URL,
        json={"session_id": session_id, "question": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.text.strip().endswith("[DONE]")


async def test_query_stream_emits_done_event_with_message_id(query_client):
    client, _, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    session_id = await _create_session(client, token)

    resp = await client.post(
        QUERY_URL,
        json={"session_id": session_id, "question": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    lines = [ln for ln in resp.text.splitlines() if ln.startswith("data: ") and ln != "data: [DONE]"]
    events = [json.loads(ln[6:]) for ln in lines]
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
    assert "message_id" in done_events[0]


# ── DB persistence ────────────────────────────────────────────────────────────

async def test_query_stream_saves_user_and_assistant_messages(query_client, db_session: AsyncSession):
    """After one full Q&A round, both user and assistant messages exist in the DB."""
    client, _, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    session_id = await _create_session(client, token)

    await client.post(
        QUERY_URL,
        json={"session_id": session_id, "question": "What is RAG?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    msg_repo = MessageRepository(db_session)
    messages = await msg_repo.get_by_session(uuid.UUID(session_id))
    roles = [m.role.value for m in messages]
    assert "user" in roles
    assert "assistant" in roles


async def test_query_stream_calls_rag_aquery_with_question(query_client):
    """RAG engine receives the user's question and the correct mode."""
    client, mock_rag, _ = query_client
    token = await _register_and_login(client, VALID_USER)
    session_id = await _create_session(client, token)

    await client.post(
        QUERY_URL,
        json={"session_id": session_id, "question": "What is RAG?", "mode": "local"},
        headers={"Authorization": f"Bearer {token}"},
    )

    mock_rag.aquery.assert_called_once()
    call_args = mock_rag.aquery.call_args
    assert call_args[0][0] == "What is RAG?"
    assert call_args[1].get("mode") == "local"
