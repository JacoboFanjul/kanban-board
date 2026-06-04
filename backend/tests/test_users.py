"""Tests for user registration and password management."""
import pytest
from fastapi.testclient import TestClient

from app import auth


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    from app import db
    db.init_db()
    auth._sessions.clear()
    yield
    auth._sessions.clear()


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def _login(client, username="user", password="password") -> str:
    return client.post("/api/login", json={"username": username, "password": password}).json()["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/register
# ---------------------------------------------------------------------------

def test_register_new_user(client):
    resp = client.post(
        "/api/register",
        json={"username": "newuser", "password": "securepassword"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data


def test_register_and_login(client):
    client.post("/api/register", json={"username": "alice", "password": "alicepass1"})
    resp = client.post("/api/login", json={"username": "alice", "password": "alicepass1"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_register_with_email(client):
    resp = client.post(
        "/api/register",
        json={"username": "bob", "password": "bobspass1", "email": "bob@example.com"},
    )
    assert resp.status_code == 201


def test_register_duplicate_username(client):
    client.post("/api/register", json={"username": "charlie", "password": "pass12345"})
    resp = client.post("/api/register", json={"username": "charlie", "password": "other1234"})
    assert resp.status_code == 409


def test_register_duplicate_with_seeded_user(client):
    resp = client.post("/api/register", json={"username": "user", "password": "newpassword"})
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = client.post("/api/register", json={"username": "dave", "password": "short"})
    assert resp.status_code == 422


def test_register_invalid_username_too_short(client):
    resp = client.post("/api/register", json={"username": "ab", "password": "validpass1"})
    assert resp.status_code == 422


def test_register_invalid_username_special_chars(client):
    resp = client.post("/api/register", json={"username": "user name!", "password": "validpass1"})
    assert resp.status_code == 422


def test_register_valid_username_with_underscores(client):
    resp = client.post("/api/register", json={"username": "user_name-1", "password": "validpass1"})
    assert resp.status_code == 201


def test_register_returns_valid_token(client):
    resp = client.post("/api/register", json={"username": "newuser2", "password": "newpassword1"})
    token = resp.json()["token"]
    me_resp = client.get("/api/me", headers=auth_headers(token))
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "newuser2"


# ---------------------------------------------------------------------------
# PUT /api/me/password
# ---------------------------------------------------------------------------

def test_change_password(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.put(
        "/api/me/password",
        json={"current_password": "password", "new_password": "newpassword1"},
        headers=h,
    )
    assert resp.status_code == 200

    # Old password no longer works
    assert client.post("/api/login", json={"username": "user", "password": "password"}).status_code == 401
    # New password works
    assert client.post("/api/login", json={"username": "user", "password": "newpassword1"}).status_code == 200


def test_change_password_wrong_current(client):
    token = _login(client)
    resp = client.put(
        "/api/me/password",
        json={"current_password": "wrongpassword", "new_password": "newpassword1"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 401


def test_change_password_too_short(client):
    token = _login(client)
    resp = client.put(
        "/api/me/password",
        json={"current_password": "password", "new_password": "short"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_change_password_requires_auth(client):
    resp = client.put(
        "/api/me/password",
        json={"current_password": "password", "new_password": "newpassword1"},
    )
    assert resp.status_code == 401
