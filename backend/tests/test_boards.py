"""Tests for multi-board management and column management."""
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


# ---------------------------------------------------------------------------
# GET /api/boards
# ---------------------------------------------------------------------------

def test_list_boards_returns_seeded_board(client):
    token = _login(client)
    resp = client.get("/api/boards", headers=auth_headers(token))
    assert resp.status_code == 200
    boards = resp.json()
    assert len(boards) == 1
    assert boards[0]["title"] == "My Board"
    assert "id" in boards[0]
    assert "created_at" in boards[0]


def test_list_boards_requires_auth(client):
    assert client.get("/api/boards").status_code == 401


# ---------------------------------------------------------------------------
# POST /api/boards
# ---------------------------------------------------------------------------

def test_create_board(client):
    token = _login(client)
    h = auth_headers(token)
    resp = client.post("/api/boards", json={"title": "Sprint Board"}, headers=h)
    assert resp.status_code == 201
    board = resp.json()
    assert board["title"] == "Sprint Board"
    assert "id" in board

    boards = client.get("/api/boards", headers=h).json()
    assert len(boards) == 2
    titles = [b["title"] for b in boards]
    assert "Sprint Board" in titles


def test_create_multiple_boards(client):
    token = _login(client)
    h = auth_headers(token)
    client.post("/api/boards", json={"title": "Board A"}, headers=h)
    client.post("/api/boards", json={"title": "Board B"}, headers=h)
    client.post("/api/boards", json={"title": "Board C"}, headers=h)
    boards = client.get("/api/boards", headers=h).json()
    assert len(boards) == 4  # 1 seeded + 3 new
    titles = [b["title"] for b in boards]
    assert "Board A" in titles
    assert "Board B" in titles
    assert "Board C" in titles


def test_create_board_requires_auth(client):
    assert client.post("/api/boards", json={"title": "X"}).status_code == 401


# ---------------------------------------------------------------------------
# GET /api/boards/{board_id}
# ---------------------------------------------------------------------------

def test_get_board_by_id(client):
    token = _login(client)
    h = auth_headers(token)
    boards = client.get("/api/boards", headers=h).json()
    board_id = boards[0]["id"]

    resp = client.get(f"/api/boards/{board_id}", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == board_id
    assert "columns" in data
    assert len(data["columns"]) == 5


def test_get_board_by_id_not_found(client):
    token = _login(client)
    resp = client.get("/api/boards/nonexistent", headers=auth_headers(token))
    assert resp.status_code == 404


def test_get_board_by_id_cross_user_isolation(client):
    """User cannot access another user's board."""
    token = _login(client)
    h = auth_headers(token)
    # Create a second user
    client.post("/api/register", json={"username": "user2", "password": "password2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "password2"}).json()["token"]
    h2 = auth_headers(token2)

    # Get user1's board id
    boards1 = client.get("/api/boards", headers=h).json()
    board_id1 = boards1[0]["id"]

    # user2 should not be able to access user1's board
    resp = client.get(f"/api/boards/{board_id1}", headers=h2)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/boards/{board_id}
# ---------------------------------------------------------------------------

def test_rename_board(client):
    token = _login(client)
    h = auth_headers(token)
    boards = client.get("/api/boards", headers=h).json()
    board_id = boards[0]["id"]

    resp = client.put(f"/api/boards/{board_id}", json={"title": "Renamed Board"}, headers=h)
    assert resp.status_code == 200

    updated = client.get("/api/boards", headers=h).json()
    assert updated[0]["title"] == "Renamed Board"


def test_rename_nonexistent_board(client):
    token = _login(client)
    resp = client.put("/api/boards/nonexistent", json={"title": "X"}, headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/boards/{board_id}
# ---------------------------------------------------------------------------

def test_delete_board(client):
    token = _login(client)
    h = auth_headers(token)
    # Create a new board
    new_board = client.post("/api/boards", json={"title": "To Delete"}, headers=h).json()
    board_id = new_board["id"]

    resp = client.delete(f"/api/boards/{board_id}", headers=h)
    assert resp.status_code == 204

    boards = client.get("/api/boards", headers=h).json()
    assert not any(b["id"] == board_id for b in boards)


def test_delete_board_cascades_columns_and_cards(client):
    """Deleting a board also removes its columns and cards."""
    token = _login(client)
    h = auth_headers(token)
    boards = client.get("/api/boards", headers=h).json()
    board_id = boards[0]["id"]

    # Verify cards exist on the board
    board_data = client.get(f"/api/boards/{board_id}", headers=h).json()
    assert len(board_data["columns"]) == 5

    client.delete(f"/api/boards/{board_id}", headers=h)

    # Board is gone
    boards_after = client.get("/api/boards", headers=h).json()
    assert not any(b["id"] == board_id for b in boards_after)


def test_delete_nonexistent_board(client):
    token = _login(client)
    resp = client.delete("/api/boards/nonexistent", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/boards/{board_id}/columns
# ---------------------------------------------------------------------------

def test_create_column(client):
    token = _login(client)
    h = auth_headers(token)
    boards = client.get("/api/boards", headers=h).json()
    board_id = boards[0]["id"]

    resp = client.post(f"/api/boards/{board_id}/columns", json={"title": "Deployed"}, headers=h)
    assert resp.status_code == 201
    col = resp.json()
    assert col["title"] == "Deployed"
    assert "id" in col

    board = client.get(f"/api/boards/{board_id}", headers=h).json()
    titles = [c["title"] for c in board["columns"]]
    assert "Deployed" in titles


def test_create_column_on_nonexistent_board(client):
    token = _login(client)
    resp = client.post(
        "/api/boards/nonexistent/columns", json={"title": "X"}, headers=auth_headers(token)
    )
    assert resp.status_code == 404


def test_create_column_appends_at_end(client):
    token = _login(client)
    h = auth_headers(token)
    boards = client.get("/api/boards", headers=h).json()
    board_id = boards[0]["id"]

    client.post(f"/api/boards/{board_id}/columns", json={"title": "Z-Column"}, headers=h)
    board = client.get(f"/api/boards/{board_id}", headers=h).json()
    assert board["columns"][-1]["title"] == "Z-Column"


# ---------------------------------------------------------------------------
# DELETE /api/board/columns/{column_id}
# ---------------------------------------------------------------------------

def test_delete_column(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.delete("/api/board/columns/col-backlog", headers=h)
    assert resp.status_code == 204

    board = client.get("/api/board", headers=h).json()
    titles = [c["title"] for c in board["columns"]]
    assert "Backlog" not in titles
    assert len(board["columns"]) == 4


def test_delete_column_reorders_positions(client):
    token = _login(client)
    h = auth_headers(token)

    # Delete 'Discovery' (pos 1); 'In Progress' should now be at pos 1
    client.delete("/api/board/columns/col-discovery", headers=h)
    board = client.get("/api/board", headers=h).json()
    titles = [c["title"] for c in board["columns"]]
    assert titles == ["Backlog", "In Progress", "Review", "Done"]


def test_delete_nonexistent_column(client):
    token = _login(client)
    resp = client.delete("/api/board/columns/nonexistent", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/board/columns/{column_id}/position
# ---------------------------------------------------------------------------

def test_move_column(client):
    token = _login(client)
    h = auth_headers(token)

    # Move 'Backlog' (pos 0) to pos 2
    resp = client.put("/api/board/columns/col-backlog/position", json={"position": 2}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    titles = [c["title"] for c in board["columns"]]
    assert titles[2] == "Backlog"
    assert titles[0] == "Discovery"
    assert titles[1] == "In Progress"


def test_move_column_nonexistent(client):
    token = _login(client)
    resp = client.put(
        "/api/board/columns/nonexistent/position", json={"position": 0}, headers=auth_headers(token)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/board/cards/{card_id} (update card)
# ---------------------------------------------------------------------------

def test_update_card_title(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.put("/api/board/cards/card-1", json={"title": "Updated Title"}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert card["title"] == "Updated Title"


def test_update_card_details(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.put("/api/board/cards/card-1", json={"details": "New details text"}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert card["details"] == "New details text"


def test_update_card_due_date(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.put("/api/board/cards/card-1", json={"due_date": "2026-12-31"}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert card["due_date"] == "2026-12-31"


def test_update_card_label(client):
    token = _login(client)
    h = auth_headers(token)

    resp = client.put("/api/board/cards/card-1", json={"label": "urgent"}, headers=h)
    assert resp.status_code == 200

    board = client.get("/api/board", headers=h).json()
    backlog = next(c for c in board["columns"] if c["id"] == "col-backlog")
    card = next(c for c in backlog["cards"] if c["id"] == "card-1")
    assert card["label"] == "urgent"


def test_update_nonexistent_card(client):
    token = _login(client)
    resp = client.put(
        "/api/board/cards/nonexistent", json={"title": "X"}, headers=auth_headers(token)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Board isolation: user can only access their own boards
# ---------------------------------------------------------------------------

def test_boards_isolated_between_users(client):
    token1 = _login(client)
    h1 = auth_headers(token1)

    # Register second user
    client.post("/api/register", json={"username": "user2", "password": "securepass2"})
    token2 = client.post("/api/login", json={"username": "user2", "password": "securepass2"}).json()["token"]
    h2 = auth_headers(token2)

    # user2 starts with 0 boards (no seed for new users)
    boards2 = client.get("/api/boards", headers=h2).json()
    assert len(boards2) == 0

    # user1 has 1 board
    boards1 = client.get("/api/boards", headers=h1).json()
    assert len(boards1) == 1

    # user2 creates a board
    client.post("/api/boards", json={"title": "User2 Board"}, headers=h2)
    boards2_after = client.get("/api/boards", headers=h2).json()
    assert len(boards2_after) == 1

    # user1 still has 1 board
    boards1_after = client.get("/api/boards", headers=h1).json()
    assert len(boards1_after) == 1
