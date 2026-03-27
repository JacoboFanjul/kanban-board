import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    auth._sessions.clear()
    yield
    auth._sessions.clear()


def _login() -> str:
    return client.post("/api/login", json={"username": "user", "password": "password"}).json()["token"]


def test_login_valid():
    response = client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_invalid_password():
    response = client.post("/api/login", json={"username": "user", "password": "wrong"})
    assert response.status_code == 401


def test_login_invalid_username():
    response = client.post("/api/login", json={"username": "nobody", "password": "password"})
    assert response.status_code == 401


def test_me_without_token():
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_with_invalid_token():
    response = client.get("/api/me", headers={"Authorization": "Bearer badtoken"})
    assert response.status_code == 401


def test_me_with_valid_token():
    token = _login()
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"username": "user"}


def test_logout_invalidates_token():
    token = _login()
    assert client.post("/api/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_without_token():
    response = client.post("/api/logout")
    assert response.status_code == 401
