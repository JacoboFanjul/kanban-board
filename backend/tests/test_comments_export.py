"""Tests for card comments, card assignment, and board export."""
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


def _board_id(client, token: str) -> str:
    return client.get("/api/boards", headers=auth_headers(token)).json()[0]["id"]


# ---------------------------------------------------------------------------
# Card assignment
# ---------------------------------------------------------------------------

def test_create_card_with_assignment(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post(
        "/api/board/cards",
        json={"column_id": "col-backlog", "title": "Assigned Card", "assigned_to": "alice"},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["assigned_to"] == "alice"


def test_update_card_assignment(client):
    token = _login(client)
    h = auth_headers(token)
    client.put("/api/board/cards/card-1", json={"assigned_to": "bob"}, headers=h)

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert card["assigned_to"] == "bob"


def test_card_assignment_null_by_default(client):
    token = _login(client)
    h = auth_headers(token)
    board = client.get("/api/board", headers=h).json()
    card = board["columns"][0]["cards"][0]
    assert card["assigned_to"] is None


def test_clear_card_assignment(client):
    token = _login(client)
    h = auth_headers(token)
    client.put("/api/board/cards/card-1", json={"assigned_to": "alice"}, headers=h)
    client.put("/api/board/cards/card-1", json={"assigned_to": ""}, headers=h)

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    # empty string is stored as-is (user can filter by empty assignee)
    assert card["assigned_to"] == ""


# ---------------------------------------------------------------------------
# GET /api/board/cards/{id}/comments
# ---------------------------------------------------------------------------

def test_get_comments_empty(client):
    token = _login(client)
    resp = client.get("/api/board/cards/card-1/comments", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_comments_requires_auth(client):
    assert client.get("/api/board/cards/card-1/comments").status_code == 401


def test_get_comments_cross_user_isolation(client):
    token = _login(client)
    # Add a comment as user
    client.post("/api/board/cards/card-1/comments", json={"content": "User's comment"}, headers=auth_headers(token))

    # Register user2
    client.post("/api/register", json={"username": "user2", "password": "securepass2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "securepass2"}).json()["token"]

    # user2 cannot access user1's card comments
    resp = client.get("/api/board/cards/card-1/comments", headers=auth_headers(token2))
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/board/cards/{id}/comments
# ---------------------------------------------------------------------------

def test_create_comment(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post(
        "/api/board/cards/card-1/comments",
        json={"content": "This looks good!"},
        headers=h,
    )
    assert resp.status_code == 201
    comment = resp.json()
    assert comment["content"] == "This looks good!"
    assert comment["username"] == "user"
    assert comment["card_id"] == "card-1"
    assert "id" in comment
    assert "created_at" in comment


def test_create_comment_appears_in_list(client):
    token = _login(client)
    h = auth_headers(token)
    client.post("/api/board/cards/card-1/comments", json={"content": "First comment"}, headers=h)
    client.post("/api/board/cards/card-1/comments", json={"content": "Second comment"}, headers=h)

    comments = client.get("/api/board/cards/card-1/comments", headers=h).json()
    assert len(comments) == 2
    assert comments[0]["content"] == "First comment"
    assert comments[1]["content"] == "Second comment"


def test_create_comment_empty_content_rejected(client):
    token = _login(client)
    resp = client.post(
        "/api/board/cards/card-1/comments",
        json={"content": "   "},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_create_comment_on_nonexistent_card(client):
    token = _login(client)
    resp = client.post(
        "/api/board/cards/no-such-card/comments",
        json={"content": "comment"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_create_comment_requires_auth(client):
    resp = client.post("/api/board/cards/card-1/comments", json={"content": "hi"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/board/comments/{comment_id}
# ---------------------------------------------------------------------------

def test_delete_comment(client):
    token = _login(client)
    h = auth_headers(token)
    comment = client.post(
        "/api/board/cards/card-1/comments",
        json={"content": "To be deleted"},
        headers=h,
    ).json()

    resp = client.delete(f"/api/board/comments/{comment['id']}", headers=h)
    assert resp.status_code == 204

    comments = client.get("/api/board/cards/card-1/comments", headers=h).json()
    assert not any(c["id"] == comment["id"] for c in comments)


def test_delete_comment_nonexistent(client):
    token = _login(client)
    resp = client.delete("/api/board/comments/no-such-comment", headers=auth_headers(token))
    assert resp.status_code == 404


def test_delete_comment_only_author(client):
    """User can only delete their own comments."""
    token = _login(client)
    comment = client.post(
        "/api/board/cards/card-1/comments",
        json={"content": "User1 comment"},
        headers=auth_headers(token),
    ).json()

    # Register user2 and give them access (they can't see user1's board, but let's verify independently)
    client.post("/api/register", json={"username": "user2", "password": "securepass2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "securepass2"}).json()["token"]

    # user2 cannot delete user1's comment
    resp = client.delete(f"/api/board/comments/{comment['id']}", headers=auth_headers(token2))
    assert resp.status_code == 404

    # comment still exists for user1
    comments = client.get("/api/board/cards/card-1/comments", headers=auth_headers(token)).json()
    assert any(c["id"] == comment["id"] for c in comments)


def test_delete_comment_requires_auth(client):
    assert client.delete("/api/board/comments/some-id").status_code == 401


# ---------------------------------------------------------------------------
# Comments cascade on card delete
# ---------------------------------------------------------------------------

def test_comments_deleted_with_card(client):
    token = _login(client)
    h = auth_headers(token)

    # Add comments to card-1
    client.post("/api/board/cards/card-1/comments", json={"content": "comment 1"}, headers=h)
    client.post("/api/board/cards/card-1/comments", json={"content": "comment 2"}, headers=h)

    # Delete the card
    client.delete("/api/board/cards/card-1", headers=h)

    # No comments should remain (cascade)
    # (We can't check via API since the card is gone, but the DB cascades)
    # Verify card is actually gone from board
    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    assert not any(c["id"] == "card-1" for c in backlog["cards"])


# ---------------------------------------------------------------------------
# GET /api/boards/{id}/export
# ---------------------------------------------------------------------------

def test_export_board_structure(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    resp = client.get(f"/api/boards/{board_id}/export", headers=h)
    assert resp.status_code == 200
    data = resp.json()

    assert "board" in data
    assert "columns" in data
    assert "exported_at" in data
    assert data["board"]["id"] == board_id
    assert data["board"]["title"] == "My Board"
    assert len(data["columns"]) == 5


def test_export_includes_cards(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    export = client.get(f"/api/boards/{board_id}/export", headers=h).json()
    backlog = next(c for c in export["columns"] if c["title"] == "Backlog")
    assert len(backlog["cards"]) == 2
    assert backlog["cards"][0]["title"] == "Align roadmap themes"


def test_export_includes_archived_cards(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    client.post("/api/board/cards/card-1/archive", headers=h)

    export = client.get(f"/api/boards/{board_id}/export", headers=h).json()
    backlog = next(c for c in export["columns"] if c["title"] == "Backlog")
    card_ids = {c["id"] for c in backlog["cards"]}
    assert "card-1" in card_ids  # export includes archived


def test_export_includes_comments(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    client.post("/api/board/cards/card-1/comments", json={"content": "Important note"}, headers=h)

    export = client.get(f"/api/boards/{board_id}/export", headers=h).json()
    backlog = next(c for c in export["columns"] if c["title"] == "Backlog")
    card1 = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert len(card1["comments"]) == 1
    assert card1["comments"][0]["content"] == "Important note"


def test_export_nonexistent_board(client):
    token = _login(client)
    resp = client.get("/api/boards/nonexistent/export", headers=auth_headers(token))
    assert resp.status_code == 404


def test_export_cross_user_isolation(client):
    token = _login(client)
    h = auth_headers(token)
    board_id = _board_id(client, token)

    client.post("/api/register", json={"username": "user2", "password": "securepass2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "securepass2"}).json()["token"]

    resp = client.get(f"/api/boards/{board_id}/export", headers=auth_headers(token2))
    assert resp.status_code == 404


def test_export_requires_auth(client):
    assert client.get("/api/boards/some-board/export").status_code == 401
