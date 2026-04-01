"""
Tests for authentication endpoints: signup, login, logout, /me, JWT validation, admin protection.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"
ADMIN_USERS_URL = "/api/v1/admin/users"

VALID_USER = {"email": "test@example.com", "password": "Password1", "full_name": "Test User"}
ADMIN_USER = {"email": "admin@example.com", "password": "Admin123!", "full_name": "Admin"}


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    """Helper: signup then login, return JWT token."""
    await client.post(SIGNUP_URL, json=payload)
    resp = await client.post(LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    return resp.json()["access_token"]


# ── Signup ────────────────────────────────────────────────────────────────────

async def test_signup_success(client: AsyncClient):
    resp = await client.post(SIGNUP_URL, json=VALID_USER)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == VALID_USER["email"]
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "hashed_password" not in body


async def test_signup_duplicate_email_returns_409(client: AsyncClient):
    await client.post(SIGNUP_URL, json=VALID_USER)
    resp = await client.post(SIGNUP_URL, json=VALID_USER)
    assert resp.status_code == 409


async def test_signup_weak_password_returns_422(client: AsyncClient):
    payload = {**VALID_USER, "password": "short"}
    resp = await client.post(SIGNUP_URL, json=payload)
    assert resp.status_code == 422


async def test_signup_password_no_digit_returns_422(client: AsyncClient):
    payload = {**VALID_USER, "password": "NoDigitsHere"}
    resp = await client.post(SIGNUP_URL, json=payload)
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient):
    await client.post(SIGNUP_URL, json=VALID_USER)
    resp = await client.post(LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_USER["password"]})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post(SIGNUP_URL, json=VALID_USER)
    resp = await client.post(LOGIN_URL, json={"email": VALID_USER["email"], "password": "WrongPass1"})
    assert resp.status_code == 401


async def test_login_nonexistent_user_returns_401(client: AsyncClient):
    resp = await client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "Password1"})
    assert resp.status_code == 401


# ── /me & JWT ─────────────────────────────────────────────────────────────────

async def test_me_returns_current_user(client: AsyncClient):
    token = await _register_and_login(client, VALID_USER)
    resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == VALID_USER["email"]


async def test_me_without_token_returns_401(client: AsyncClient):
    resp = await client.get(ME_URL)
    assert resp.status_code == 401


async def test_me_with_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get(ME_URL, headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


# ── Admin protection ──────────────────────────────────────────────────────────

async def test_admin_route_blocked_for_regular_user(client: AsyncClient):
    token = await _register_and_login(client, VALID_USER)
    resp = await client.get(ADMIN_USERS_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_logout_returns_200(client: AsyncClient):
    token = await _register_and_login(client, VALID_USER)
    resp = await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
