"""
Tests for session CRUD endpoints.

All tests use an in-memory SQLite DB and mocked RAG engine (same pattern as test_documents.py).
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.base import Base
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="function")

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
SESSIONS_URL = "/api/v1/sessions/"

USER_A = {"email": "usera@example.com", "password": "Password1", "full_name": "User A"}
USER_B = {"email": "userb@example.com", "password": "Password1", "full_name": "User B"}


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
async def session_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    await client.post(SIGNUP_URL, json=payload)
    resp = await client.post(LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    return resp.json()["access_token"]


# ── Create ────────────────────────────────────────────────────────────────────

async def test_create_session_default_mode_returns_201(session_client):
    token = await _register_and_login(session_client, USER_A)
    resp = await session_client.post(
        SESSIONS_URL,
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["query_mode"] == "hybrid"
    assert body["title"].startswith("新對話")
    assert body["message_count"] == 0


async def test_create_session_custom_mode(session_client):
    token = await _register_and_login(session_client, USER_A)
    resp = await session_client.post(
        SESSIONS_URL,
        json={"query_mode": "local"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["query_mode"] == "local"


async def test_create_session_without_token_returns_401(session_client):
    resp = await session_client.post(SESSIONS_URL, json={})
    assert resp.status_code == 401


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_sessions_returns_own_only(session_client):
    token_a = await _register_and_login(session_client, USER_A)
    token_b = await _register_and_login(session_client, USER_B)

    for _ in range(3):
        await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token_a}"})
    await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token_b}"})

    resp = await session_client.get(SESSIONS_URL, headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["sessions"]) == 3


async def test_list_sessions_without_token_returns_401(session_client):
    resp = await session_client.get(SESSIONS_URL)
    assert resp.status_code == 401


# ── Get detail ────────────────────────────────────────────────────────────────

async def test_get_session_returns_detail(session_client):
    token = await _register_and_login(session_client, USER_A)
    create_resp = await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token}"})
    session_id = create_resp.json()["id"]

    resp = await session_client.get(
        f"{SESSIONS_URL}{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "session" in body
    assert "messages" in body
    assert body["messages"] == []


async def test_get_session_other_user_returns_403(session_client):
    token_a = await _register_and_login(session_client, USER_A)
    token_b = await _register_and_login(session_client, USER_B)

    create_resp = await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token_a}"})
    session_id = create_resp.json()["id"]

    resp = await session_client.get(
        f"{SESSIONS_URL}{session_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


async def test_get_nonexistent_session_returns_404(session_client):
    import uuid
    token = await _register_and_login(session_client, USER_A)
    resp = await session_client.get(
        f"{SESSIONS_URL}{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── Rename ────────────────────────────────────────────────────────────────────

async def test_rename_session_updates_title(session_client):
    token = await _register_and_login(session_client, USER_A)
    create_resp = await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token}"})
    session_id = create_resp.json()["id"]

    resp = await session_client.patch(
        f"{SESSIONS_URL}{session_id}/title",
        json={"title": "My Custom Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Custom Title"


async def test_rename_session_other_user_returns_403(session_client):
    token_a = await _register_and_login(session_client, USER_A)
    token_b = await _register_and_login(session_client, USER_B)

    create_resp = await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token_a}"})
    session_id = create_resp.json()["id"]

    resp = await session_client.patch(
        f"{SESSIONS_URL}{session_id}/title",
        json={"title": "Hijacked"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_session_returns_204(session_client):
    token = await _register_and_login(session_client, USER_A)
    create_resp = await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token}"})
    session_id = create_resp.json()["id"]

    resp = await session_client.delete(
        f"{SESSIONS_URL}{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    get_resp = await session_client.get(
        f"{SESSIONS_URL}{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 404


async def test_delete_session_other_user_returns_403(session_client):
    token_a = await _register_and_login(session_client, USER_A)
    token_b = await _register_and_login(session_client, USER_B)

    create_resp = await session_client.post(SESSIONS_URL, json={}, headers={"Authorization": f"Bearer {token_a}"})
    session_id = create_resp.json()["id"]

    resp = await session_client.delete(
        f"{SESSIONS_URL}{session_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403
