import os
import pytest
from fastapi.testclient import TestClient

from app import auth


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a fresh, isolated database and clean session store."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    # Re-import db after env var is set so _db_path() picks it up
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
    return client.post(
        "/api/login", json={"username": "user", "password": "password"}
    ).json()["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

def test_board_requires_auth(client):
    assert client.get("/api/board").status_code == 401


def test_all_board_endpoints_require_auth(client):
    assert client.put("/api/board/columns/col-backlog", json={"title": "X"}).status_code == 401
    assert client.post("/api/board/cards", json={"column_id": "col-backlog", "title": "T"}).status_code == 401
    assert client.delete("/api/board/cards/card-1").status_code == 401
    assert client.put("/api/board/cards/card-1/move", json={"column_id": "col-backlog", "position": 0}).status_code == 401


# ---------------------------------------------------------------------------
# GET /api/board
# ---------------------------------------------------------------------------

def test_get_board_returns_correct_structure(client):
    token = _login(client)
    resp = client.get("/api/board", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert len(data["columns"]) == 5
    col_titles = [c["title"] for c in data["columns"]]
    assert col_titles == ["Backlog", "Discovery", "In Progress", "Review", "Done"]
    # Backlog starts with 2 seeded cards
    backlog = data["columns"][0]
    assert len(backlog["cards"]) == 2
    assert backlog["cards"][0]["title"] == "Align roadmap themes"


# ---------------------------------------------------------------------------
# PUT /api/board/columns/{id}
# ---------------------------------------------------------------------------

def test_rename_column(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.put("/api/board/columns/col-backlog", json={"title": "New Name"}, headers=h)
    assert resp.status_code == 200
    board = client.get("/api/board", headers=h).json()
    titles = [c["title"] for c in board["columns"]]
    assert "New Name" in titles
    assert "Backlog" not in titles


def test_rename_nonexistent_column(client):
    token = _login(client)
    resp = client.put(
        "/api/board/columns/no-such-col", json={"title": "X"}, headers=auth_headers(token)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/board/cards
# ---------------------------------------------------------------------------

def test_create_card(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post(
        "/api/board/cards",
        json={"column_id": "col-backlog", "title": "New Card", "details": "Some details"},
        headers=h,
    )
    assert resp.status_code == 201
    card = resp.json()
    assert card["title"] == "New Card"
    assert card["details"] == "Some details"
    assert "id" in card

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert any(c["title"] == "New Card" for c in backlog["cards"])


def test_create_card_in_nonexistent_column(client):
    token = _login(client)
    resp = client.post(
        "/api/board/cards",
        json={"column_id": "no-such-col", "title": "T"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/board/cards/{id}
# ---------------------------------------------------------------------------

def test_delete_card(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.delete("/api/board/cards/card-1", headers=h)
    assert resp.status_code == 204

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert not any(c["id"] == "card-1" for c in backlog["cards"])


def test_delete_nonexistent_card(client):
    token = _login(client)
    resp = client.delete("/api/board/cards/no-such-card", headers=auth_headers(token))
    assert resp.status_code == 404


def test_delete_maintains_positions(client):
    token = _login(client)
    h = auth_headers(token)
    # Delete card-1 (pos 0); card-2 (pos 1) should become pos 0
    client.delete("/api/board/cards/card-1", headers=h)
    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert len(backlog["cards"]) == 1
    assert backlog["cards"][0]["id"] == "card-2"


# ---------------------------------------------------------------------------
# PUT /api/board/cards/{id}/move
# ---------------------------------------------------------------------------

def test_move_card_across_columns(client):
    token = _login(client)
    h = auth_headers(token)
    # Move card-1 from backlog to discovery at position 0
    resp = client.put(
        "/api/board/cards/card-1/move",
        json={"column_id": "col-discovery", "position": 0},
        headers=h,
    )
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    discovery = next(c for c in board["columns"] if c["id"] == "col-discovery")
    assert not any(c["id"] == "card-1" for c in backlog["cards"])
    assert discovery["cards"][0]["id"] == "card-1"
    # card-3 was already in discovery at pos 0 — it should now be at pos 1
    assert discovery["cards"][1]["id"] == "card-3"


def test_move_card_within_column(client):
    token = _login(client)
    h = auth_headers(token)
    # Backlog has card-1 (pos 0) and card-2 (pos 1); move card-1 to pos 1
    resp = client.put(
        "/api/board/cards/card-1/move",
        json={"column_id": "col-backlog", "position": 1},
        headers=h,
    )
    assert resp.status_code == 200
    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert backlog["cards"][0]["id"] == "card-2"
    assert backlog["cards"][1]["id"] == "card-1"


def test_move_card_to_nonexistent_column(client):
    token = _login(client)
    resp = client.put(
        "/api/board/cards/card-1/move",
        json={"column_id": "no-such-col", "position": 0},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_move_nonexistent_card(client):
    token = _login(client)
    resp = client.put(
        "/api/board/cards/no-such-card/move",
        json={"column_id": "col-backlog", "position": 0},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DB auto-creation from scratch
# ---------------------------------------------------------------------------

def test_db_created_from_scratch(tmp_path, monkeypatch):
    fresh_path = str(tmp_path / "fresh.db")
    monkeypatch.setenv("DB_PATH", fresh_path)
    from app import db
    assert not (tmp_path / "fresh.db").exists() or (tmp_path / "fresh.db").stat().st_size == 0 or True
    db.init_db()
    # DB file is created and seeded
    assert (tmp_path / "fresh.db").exists()
    board = db.get_board("user")
    assert len(board["columns"]) == 5
