"""Tests for priority, archiving, search, WIP limits, and card timestamps."""
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


def _login(client) -> str:
    return client.post("/api/login", json={"username": "user", "password": "password"}).json()["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _board_id(client, token: str) -> str:
    return client.get("/api/boards", headers=auth_headers(token)).json()[0]["id"]


# ---------------------------------------------------------------------------
# Card priority
# ---------------------------------------------------------------------------

def test_create_card_with_priority(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post(
        "/api/board/cards",
        json={"column_id": "col-backlog", "title": "Priority Card", "priority": "high"},
        headers=h,
    )
    assert resp.status_code == 201
    card = resp.json()
    assert card["priority"] == "high"


def test_update_card_priority(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.put("/api/board/cards/card-1", json={"priority": "critical"}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert card["priority"] == "critical"


def test_create_card_no_priority_defaults_null(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post(
        "/api/board/cards",
        json={"column_id": "col-backlog", "title": "No Priority"},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["priority"] is None


def test_card_has_created_at_timestamp(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post(
        "/api/board/cards",
        json={"column_id": "col-backlog", "title": "Timestamped Card"},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["created_at"] is not None


def test_board_returns_priority_field(client):
    token = _login(client)
    h = auth_headers(token)
    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert "priority" in backlog["cards"][0]


# ---------------------------------------------------------------------------
# Card archiving
# ---------------------------------------------------------------------------

def test_archive_card(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.post("/api/board/cards/card-1/archive", headers=h)
    assert resp.status_code == 200

    # Card no longer appears in the board
    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert not any(c["id"] == "card-1" for c in backlog["cards"])


def test_archived_cards_appear_in_archive_endpoint(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    client.post("/api/board/cards/card-1/archive", headers=h)
    client.post("/api/board/cards/card-2/archive", headers=h)

    archived = client.get(f"/api/boards/{board_id}/archived", headers=h).json()
    assert len(archived) == 2
    ids = {c["id"] for c in archived}
    assert "card-1" in ids
    assert "card-2" in ids


def test_unarchive_card(client):
    token = _login(client)
    h = auth_headers(token)

    client.post("/api/board/cards/card-1/archive", headers=h)
    resp = client.post("/api/board/cards/card-1/unarchive", headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert any(c["id"] == "card-1" for c in backlog["cards"])


def test_archive_nonexistent_card(client):
    token = _login(client)
    resp = client.post("/api/board/cards/no-such-card/archive", headers=auth_headers(token))
    assert resp.status_code == 404


def test_archive_card_cross_user_isolation(client):
    """User cannot archive another user's card."""
    token = _login(client)
    # Register second user
    client.post("/api/register", json={"username": "user2", "password": "securepass2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "securepass2"}).json()["token"]

    # user2 tries to archive user1's card
    resp = client.post("/api/board/cards/card-1/archive", headers=auth_headers(token2))
    assert resp.status_code == 404

    # card is still visible to user1
    board = client.get("/api/board", headers=auth_headers(token)).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert any(c["id"] == "card-1" for c in backlog["cards"])


def test_archived_endpoint_requires_auth(client):
    board_id = "some-board"
    assert client.get(f"/api/boards/{board_id}/archived").status_code == 401


# ---------------------------------------------------------------------------
# Search & filter
# ---------------------------------------------------------------------------

def test_search_by_text(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    results = client.get(f"/api/boards/{board_id}/search?q=roadmap", headers=h).json()
    assert len(results) == 1
    assert results[0]["title"] == "Align roadmap themes"


def test_search_returns_column_title(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    results = client.get(f"/api/boards/{board_id}/search?q=roadmap", headers=h).json()
    assert results[0]["column_title"] == "Backlog"


def test_search_by_label(client):
    token = _login(client)
    h = auth_headers(token)

    client.put("/api/board/cards/card-1", json={"label": "bug"}, headers=h)
    client.put("/api/board/cards/card-2", json={"label": "feature"}, headers=h)
    client.put("/api/board/cards/card-3", json={"label": "bug"}, headers=h)

    board_id = _board_id(client, token)
    results = client.get(f"/api/boards/{board_id}/search?label=bug", headers=h).json()
    assert len(results) == 2
    ids = {r["id"] for r in results}
    assert "card-1" in ids
    assert "card-3" in ids


def test_search_by_priority(client):
    token = _login(client)
    h = auth_headers(token)

    client.put("/api/board/cards/card-1", json={"priority": "high"}, headers=h)
    client.put("/api/board/cards/card-3", json={"priority": "high"}, headers=h)
    client.put("/api/board/cards/card-5", json={"priority": "low"}, headers=h)

    board_id = _board_id(client, token)
    results = client.get(f"/api/boards/{board_id}/search?priority=high", headers=h).json()
    assert len(results) == 2


def test_search_combined_filters(client):
    token = _login(client)
    h = auth_headers(token)

    client.put("/api/board/cards/card-1", json={"label": "bug", "priority": "high"}, headers=h)
    client.put("/api/board/cards/card-2", json={"label": "bug", "priority": "low"}, headers=h)

    board_id = _board_id(client, token)
    results = client.get(
        f"/api/boards/{board_id}/search?label=bug&priority=high", headers=h
    ).json()
    assert len(results) == 1
    assert results[0]["id"] == "card-1"


def test_search_excludes_archived(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    client.post("/api/board/cards/card-1/archive", headers=h)
    results = client.get(f"/api/boards/{board_id}/search?q=roadmap", headers=h).json()
    assert all(r["id"] != "card-1" for r in results)


def test_search_empty_query_returns_all(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    results = client.get(f"/api/boards/{board_id}/search", headers=h).json()
    assert len(results) == 8  # all seed cards


def test_search_requires_auth(client):
    assert client.get("/api/boards/some-board/search?q=test").status_code == 401


def test_search_cross_user_isolation(client):
    token = _login(client)
    h = auth_headers(token)
    boards1 = client.get("/api/boards", headers=h).json()
    board_id1 = boards1[0]["id"]

    client.post("/api/register", json={"username": "user2", "password": "securepass2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "securepass2"}).json()["token"]

    # user2 cannot search user1's board
    results = client.get(
        f"/api/boards/{board_id1}/search?q=roadmap",
        headers=auth_headers(token2),
    ).json()
    assert results == []


# ---------------------------------------------------------------------------
# Column WIP limits
# ---------------------------------------------------------------------------

def test_set_wip_limit(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.put("/api/board/columns/col-backlog/wip-limit", json={"wip_limit": 3}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert backlog["wip_limit"] == 3


def test_set_wip_limit_to_null(client):
    token = _login(client)
    h = auth_headers(token)

    client.put("/api/board/columns/col-backlog/wip-limit", json={"wip_limit": 3}, headers=h)
    resp = client.put("/api/board/columns/col-backlog/wip-limit", json={"wip_limit": None}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert backlog["wip_limit"] is None


def test_set_wip_limit_nonexistent_column(client):
    token = _login(client)
    resp = client.put(
        "/api/board/columns/no-such-col/wip-limit",
        json={"wip_limit": 5},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_wip_limit_requires_auth(client):
    assert client.put(
        "/api/board/columns/col-backlog/wip-limit", json={"wip_limit": 5}
    ).status_code == 401


def test_new_board_columns_have_null_wip_limit(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    col = client.post(f"/api/boards/{board_id}/columns", json={"title": "New"}, headers=h).json()
    assert col["wip_limit"] is None

    board = client.get(f"/api/boards/{board_id}", headers=h).json()
    new_col = next(c for c in board["columns"] if c["id"] == col["id"])
    assert new_col["wip_limit"] is None
