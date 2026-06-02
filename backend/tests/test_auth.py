import pytest
from fastapi.testclient import TestClient

from app import auth


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a fresh, isolated database and clean session store."""
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


def _login(client) -> str:
    return client.post("/api/login", json={"username": "user", "password": "password"}).json()["token"]


def test_login_valid(client):
    response = client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_invalid_password(client):
    response = client.post("/api/login", json={"username": "user", "password": "wrong"})
    assert response.status_code == 401


def test_login_invalid_username(client):
    response = client.post("/api/login", json={"username": "nobody", "password": "password"})
    assert response.status_code == 401


def test_me_without_token(client):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_with_invalid_token(client):
    response = client.get("/api/me", headers={"Authorization": "Bearer badtoken"})
    assert response.status_code == 401


def test_me_with_valid_token(client):
    token = _login(client)
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"username": "user"}


def test_logout_invalidates_token(client):
    token = _login(client)
    assert client.post("/api/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_without_token(client):
    response = client.post("/api/logout")
    assert response.status_code == 401
