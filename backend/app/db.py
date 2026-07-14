import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from app.security import hash_password

_SEED_COLUMNS = [
    ("col-backlog",   "Backlog",     0),
    ("col-discovery", "Discovery",   1),
    ("col-progress",  "In Progress", 2),
    ("col-review",    "Review",      3),
    ("col-done",      "Done",        4),
]

_SEED_CARDS = [
    ("card-1", "col-backlog",   "Align roadmap themes",    "Draft quarterly themes with impact statements and metrics.", 0),
    ("card-2", "col-backlog",   "Gather customer signals",  "Review support tags, sales notes, and churn feedback.",     1),
    ("card-3", "col-discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.",      0),
    ("card-4", "col-progress",  "Refine status language",   "Standardize column labels and tone across the board.",      0),
    ("card-5", "col-progress",  "Design card layout",       "Add hierarchy and spacing for scanning dense lists.",       1),
    ("card-6", "col-review",    "QA micro-interactions",    "Verify hover, focus, and loading states.",                  0),
    ("card-7", "col-done",      "Ship marketing page",      "Final copy approved and asset pack delivered.",             0),
    ("card-8", "col-done",      "Close onboarding sprint",  "Document release notes and share internally.",              1),
]


def _db_path() -> str:
    return os.environ.get("DB_PATH", "/data/pm.db")


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply schema migrations for existing databases."""
    # Check boards table for UNIQUE(username) constraint and add title column
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='boards'"
    ).fetchone()
    if row:
        sql = row[0]
        boards_cols = {r[1] for r in conn.execute("PRAGMA table_info(boards)").fetchall()}
        needs_title = "title" not in boards_cols
        needs_unique_drop = "UNIQUE(username)" in sql

        if needs_title or needs_unique_drop:
            conn.execute("ALTER TABLE boards RENAME TO _boards_old")
            conn.execute("""
                CREATE TABLE boards (
                    id         TEXT PRIMARY KEY,
                    username   TEXT NOT NULL REFERENCES users(username),
                    title      TEXT NOT NULL DEFAULT 'My Board',
                    created_at TEXT NOT NULL
                )
            """)
            if needs_title:
                conn.execute(
                    "INSERT INTO boards SELECT id, username, 'My Board', created_at FROM _boards_old"
                )
            else:
                conn.execute(
                    "INSERT INTO boards SELECT id, username, title, created_at FROM _boards_old"
                )
            conn.execute("DROP TABLE _boards_old")

    # Add new columns to cards if missing
    card_cols = {r[1] for r in conn.execute("PRAGMA table_info(cards)").fetchall()}
    if "due_date" not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN due_date TEXT")
    if "label" not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN label TEXT")
    if "priority" not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN priority TEXT")
    if "archived" not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
    if "created_at" not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN created_at TEXT")
    if "assigned_to" not in card_cols:
        conn.execute("ALTER TABLE cards ADD COLUMN assigned_to TEXT")

    # Add wip_limit to columns if missing
    col_cols = {r[1] for r in conn.execute("PRAGMA table_info(columns)").fetchall()}
    if "wip_limit" not in col_cols:
        conn.execute("ALTER TABLE columns ADD COLUMN wip_limit INTEGER")

    # Add email column to users if missing
    user_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")

    conn.commit()


def init_db() -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email         TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id         TEXT PRIMARY KEY,
            username   TEXT NOT NULL REFERENCES users(username),
            title      TEXT NOT NULL DEFAULT 'My Board',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id        TEXT PRIMARY KEY,
            board_id  TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            title     TEXT NOT NULL,
            position  INTEGER NOT NULL,
            wip_limit INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id          TEXT PRIMARY KEY,
            column_id   TEXT NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            details     TEXT NOT NULL DEFAULT '',
            position    INTEGER NOT NULL,
            due_date    TEXT,
            label       TEXT,
            priority    TEXT,
            archived    INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT,
            assigned_to TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS card_comments (
            id         TEXT PRIMARY KEY,
            card_id    TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            username   TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    _migrate(conn)

    # Seed only if no users exist yet
    if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        conn.close()
        return

    board_id = secrets.token_hex(8)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT INTO users VALUES (?, ?, ?)", ("user", hash_password("password"), None))
    conn.execute("INSERT INTO boards VALUES (?, ?, ?, ?)", (board_id, "user", "My Board", now))
    for col_id, title, pos in _SEED_COLUMNS:
        conn.execute(
            "INSERT INTO columns(id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col_id, board_id, title, pos),
        )
    for card_id, col_id, title, details, pos in _SEED_CARDS:
        conn.execute(
            "INSERT INTO cards(id, column_id, title, details, position, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (card_id, col_id, title, details, pos, now),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# User queries
# ---------------------------------------------------------------------------

def get_password_hash(username: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        return row["password_hash"] if row else None


def create_user(username: str, password: str, email: str | None = None) -> bool:
    """Returns False if username already exists."""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users(username, password_hash, email) VALUES (?, ?, ?)",
                (username, hash_password(password), email),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def update_password(username: str, new_password: str) -> bool:
    with get_conn() as conn:
        result = conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(new_password), username),
        )
        return result.rowcount == 1


def list_users() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, email FROM users ORDER BY username"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Board queries
# ---------------------------------------------------------------------------

def get_board_id(conn: sqlite3.Connection, username: str) -> str | None:
    """Returns the first board id for a user (backward compat)."""
    row = conn.execute(
        "SELECT id FROM boards WHERE username = ? ORDER BY created_at LIMIT 1", (username,)
    ).fetchone()
    return row["id"] if row else None


def list_boards(username: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM boards WHERE username = ? ORDER BY created_at",
            (username,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_board(username: str, title: str) -> dict:
    board_id = secrets.token_hex(8)
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO boards(id, username, title, created_at) VALUES (?, ?, ?, ?)",
            (board_id, username, title, now),
        )
    return {"id": board_id, "title": title, "created_at": now}


def rename_board(username: str, board_id: str, title: str) -> bool:
    with get_conn() as conn:
        result = conn.execute(
            "UPDATE boards SET title = ? WHERE id = ? AND username = ?",
            (title, board_id, username),
        )
        return result.rowcount == 1


def delete_board(username: str, board_id: str) -> bool:
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM boards WHERE id = ? AND username = ?",
            (board_id, username),
        )
        return result.rowcount == 1


def _board_owned_by(conn: sqlite3.Connection, username: str, board_id: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM boards WHERE id = ? AND username = ?", (board_id, username)
        ).fetchone()
    )


def _column_owned_by(conn: sqlite3.Connection, username: str, column_id: str) -> bool:
    return bool(
        conn.execute(
            """
            SELECT 1 FROM columns
            JOIN boards ON columns.board_id = boards.id
            WHERE columns.id = ? AND boards.username = ?
            """,
            (column_id, username),
        ).fetchone()
    )


def _card_owned_by(conn: sqlite3.Connection, username: str, card_id: str) -> bool:
    return bool(
        conn.execute(
            """
            SELECT 1 FROM cards
            JOIN columns ON cards.column_id = columns.id
            JOIN boards ON columns.board_id = boards.id
            WHERE cards.id = ? AND boards.username = ?
            """,
            (card_id, username),
        ).fetchone()
    )


def get_board(username: str, board_id: str | None = None) -> dict:
    with get_conn() as conn:
        if board_id:
            if not _board_owned_by(conn, username, board_id):
                return {"columns": []}
            bid = board_id
        else:
            bid = get_board_id(conn, username)
        if not bid:
            return {"columns": []}
        board_row = conn.execute(
            "SELECT id, title FROM boards WHERE id = ?", (bid,)
        ).fetchone()
        cols = conn.execute(
            "SELECT id, title, wip_limit FROM columns WHERE board_id = ? ORDER BY position",
            (bid,),
        ).fetchall()
        result = []
        for col in cols:
            cards = conn.execute(
                "SELECT id, title, details, due_date, label, priority, created_at, assigned_to "
                "FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
                (col["id"],),
            ).fetchall()
            result.append({
                "id": col["id"],
                "title": col["title"],
                "wip_limit": col["wip_limit"],
                "cards": [dict(c) for c in cards],
            })
        return {
            "id": board_row["id"],
            "title": board_row["title"],
            "columns": result,
        }


_CARD_LIST_SELECT = """
    SELECT cards.id, cards.title, cards.details, cards.due_date,
           cards.label, cards.priority, cards.created_at, cards.assigned_to,
           cards.column_id, columns.title AS column_title
    FROM cards
    JOIN columns ON cards.column_id = columns.id
"""


def search_cards(username: str, board_id: str, q: str = "", label: str = "", priority: str = "") -> list[dict]:
    with get_conn() as conn:
        if not _board_owned_by(conn, username, board_id):
            return []
        conditions = [
            "cards.archived = 0",
            "columns.board_id = ?",
        ]
        params: list = [board_id]
        if q:
            conditions.append("(cards.title LIKE ? OR cards.details LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if label:
            conditions.append("cards.label = ?")
            params.append(label)
        if priority:
            conditions.append("cards.priority = ?")
            params.append(priority)
        where = " AND ".join(conditions)
        rows = conn.execute(
            f"{_CARD_LIST_SELECT} WHERE {where} ORDER BY columns.position, cards.position",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_archived_cards(username: str, board_id: str) -> list[dict]:
    with get_conn() as conn:
        if not _board_owned_by(conn, username, board_id):
            return []
        rows = conn.execute(
            f"{_CARD_LIST_SELECT} "
            "WHERE columns.board_id = ? AND cards.archived = 1 ORDER BY cards.rowid DESC",
            (board_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _set_card_archived(username: str, card_id: str, archived: int) -> bool:
    with get_conn() as conn:
        if not _card_owned_by(conn, username, card_id):
            return False
        conn.execute("UPDATE cards SET archived = ? WHERE id = ?", (archived, card_id))
        return True


def archive_card(username: str, card_id: str) -> bool:
    return _set_card_archived(username, card_id, 1)


def unarchive_card(username: str, card_id: str) -> bool:
    return _set_card_archived(username, card_id, 0)


# ---------------------------------------------------------------------------
# Column mutations
# ---------------------------------------------------------------------------

def rename_column(username: str, column_id: str, title: str) -> bool:
    with get_conn() as conn:
        result = conn.execute(
            "UPDATE columns SET title = ? WHERE id = ? AND board_id IN "
            "(SELECT id FROM boards WHERE username = ?)",
            (title, column_id, username),
        )
        return result.rowcount == 1


def create_column(username: str, board_id: str, title: str) -> dict | None:
    with get_conn() as conn:
        if not _board_owned_by(conn, username, board_id):
            return None
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM columns WHERE board_id = ?",
            (board_id,),
        ).fetchone()[0]
        col_id = secrets.token_hex(8)
        position = max_pos + 1
        conn.execute(
            "INSERT INTO columns(id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col_id, board_id, title, position),
        )
        return {"id": col_id, "title": title, "position": position, "wip_limit": None}


def set_column_wip_limit(username: str, column_id: str, wip_limit: int | None) -> bool:
    with get_conn() as conn:
        result = conn.execute(
            """
            UPDATE columns SET wip_limit = ?
            WHERE id = ? AND board_id IN (SELECT id FROM boards WHERE username = ?)
            """,
            (wip_limit, column_id, username),
        )
        return result.rowcount == 1


def delete_column(username: str, column_id: str) -> bool:
    with get_conn() as conn:
        # Verify column belongs to this user's board
        row = conn.execute(
            """
            SELECT columns.id, columns.board_id, columns.position
            FROM columns
            JOIN boards ON columns.board_id = boards.id
            WHERE columns.id = ? AND boards.username = ?
            """,
            (column_id, username),
        ).fetchone()
        if not row:
            return False
        board_id = row["board_id"]
        position = row["position"]
        conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))
        conn.execute(
            "UPDATE columns SET position = position - 1 WHERE board_id = ? AND position > ?",
            (board_id, position),
        )
        return True


def move_column(username: str, column_id: str, target_position: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT columns.id, columns.board_id, columns.position
            FROM columns
            JOIN boards ON columns.board_id = boards.id
            WHERE columns.id = ? AND boards.username = ?
            """,
            (column_id, username),
        ).fetchone()
        if not row:
            return False
        board_id = row["board_id"]
        src_pos = row["position"]

        col_count = conn.execute(
            "SELECT COUNT(*) FROM columns WHERE board_id = ?", (board_id,)
        ).fetchone()[0]
        target_position = max(0, min(target_position, col_count - 1))

        if src_pos == target_position:
            return True

        if target_position < src_pos:
            conn.execute(
                "UPDATE columns SET position = position + 1 "
                "WHERE board_id = ? AND position >= ? AND position < ? AND id != ?",
                (board_id, target_position, src_pos, column_id),
            )
        else:
            conn.execute(
                "UPDATE columns SET position = position - 1 "
                "WHERE board_id = ? AND position > ? AND position <= ? AND id != ?",
                (board_id, src_pos, target_position, column_id),
            )
        conn.execute(
            "UPDATE columns SET position = ? WHERE id = ?",
            (target_position, column_id),
        )
        return True


# ---------------------------------------------------------------------------
# Card mutations
# ---------------------------------------------------------------------------

def create_card(
    username: str, column_id: str, title: str, details: str,
    due_date: str | None = None, label: str | None = None,
    priority: str | None = None, assigned_to: str | None = None,
) -> dict | None:
    with get_conn() as conn:
        if not _column_owned_by(conn, username, column_id):
            return None
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM cards WHERE column_id = ? AND archived = 0",
            (column_id,),
        ).fetchone()[0]
        card_id = secrets.token_hex(8)
        position = max_pos + 1
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO cards(id, column_id, title, details, position, due_date, label, priority, assigned_to, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (card_id, column_id, title, details, position, due_date, label, priority, assigned_to, now),
        )
        return {
            "id": card_id, "title": title, "details": details,
            "due_date": due_date, "label": label, "priority": priority,
            "assigned_to": assigned_to, "created_at": now,
        }


def update_card(
    username: str, card_id: str,
    title: str | None = None,
    details: str | None = None,
    due_date: str | None = None,
    label: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
) -> bool:
    with get_conn() as conn:
        if not _card_owned_by(conn, username, card_id):
            return False
        fields = {
            "title": title,
            "details": details,
            "due_date": due_date,
            "label": label,
            "priority": priority,
            "assigned_to": assigned_to,
        }
        set_cols = [f"{col} = ?" for col, value in fields.items() if value is not None]
        if not set_cols:
            return True
        params = [value for value in fields.values() if value is not None]
        params.append(card_id)
        conn.execute(
            f"UPDATE cards SET {', '.join(set_cols)} WHERE id = ?",
            params,
        )
        return True


def delete_card(username: str, card_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT cards.id, cards.column_id, cards.position
            FROM cards
            JOIN columns ON cards.column_id = columns.id
            JOIN boards ON columns.board_id = boards.id
            WHERE cards.id = ? AND boards.username = ?
            """,
            (card_id, username),
        ).fetchone()
        if not row:
            return False
        col_id = row["column_id"]
        position = row["position"]
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        conn.execute(
            "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
            (col_id, position),
        )
        return True


def move_card(username: str, card_id: str, target_column_id: str, target_position: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT cards.id, cards.column_id, cards.position
            FROM cards
            JOIN columns ON cards.column_id = columns.id
            JOIN boards ON columns.board_id = boards.id
            WHERE cards.id = ? AND boards.username = ?
            """,
            (card_id, username),
        ).fetchone()
        if not row:
            return False
        # Verify target column belongs to this user's board
        if not _column_owned_by(conn, username, target_column_id):
            return False

        src_col_id = row["column_id"]
        src_pos = row["position"]

        col_card_count = conn.execute(
            "SELECT COUNT(*) FROM cards WHERE column_id = ?",
            (target_column_id,),
        ).fetchone()[0]
        if src_col_id == target_column_id:
            max_pos = col_card_count - 1
        else:
            max_pos = col_card_count
        target_position = max(0, min(target_position, max_pos))

        if src_col_id == target_column_id and src_pos == target_position:
            return True

        if src_col_id == target_column_id:
            if target_position < src_pos:
                conn.execute(
                    "UPDATE cards SET position = position + 1 "
                    "WHERE column_id = ? AND position >= ? AND position < ? AND id != ?",
                    (src_col_id, target_position, src_pos, card_id),
                )
            else:
                conn.execute(
                    "UPDATE cards SET position = position - 1 "
                    "WHERE column_id = ? AND position > ? AND position <= ? AND id != ?",
                    (src_col_id, src_pos, target_position, card_id),
                )
            conn.execute(
                "UPDATE cards SET position = ? WHERE id = ?",
                (target_position, card_id),
            )
        else:
            conn.execute(
                "UPDATE cards SET position = position - 1 "
                "WHERE column_id = ? AND position > ?",
                (src_col_id, src_pos),
            )
            conn.execute(
                "UPDATE cards SET position = position + 1 "
                "WHERE column_id = ? AND position >= ?",
                (target_column_id, target_position),
            )
            conn.execute(
                "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
                (target_column_id, target_position, card_id),
            )
        return True


# ---------------------------------------------------------------------------
# Card comments
# ---------------------------------------------------------------------------

def get_card_comments(username: str, card_id: str) -> list[dict]:
    with get_conn() as conn:
        if not _card_owned_by(conn, username, card_id):
            return []
        rows = conn.execute(
            "SELECT id, card_id, username, content, created_at "
            "FROM card_comments WHERE card_id = ? ORDER BY created_at",
            (card_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_comment(username: str, card_id: str, content: str) -> dict | None:
    with get_conn() as conn:
        if not _card_owned_by(conn, username, card_id):
            return None
        comment_id = secrets.token_hex(8)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO card_comments(id, card_id, username, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (comment_id, card_id, username, content, now),
        )
        return {"id": comment_id, "card_id": card_id, "username": username, "content": content, "created_at": now}


def delete_comment(username: str, comment_id: str) -> bool:
    with get_conn() as conn:
        # Only the comment author can delete their comment
        result = conn.execute(
            "DELETE FROM card_comments WHERE id = ? AND username = ?",
            (comment_id, username),
        )
        return result.rowcount == 1


# ---------------------------------------------------------------------------
# Board export
# ---------------------------------------------------------------------------

def export_board(username: str, board_id: str) -> dict | None:
    with get_conn() as conn:
        if not _board_owned_by(conn, username, board_id):
            return None
        board_row = conn.execute(
            "SELECT id, title, created_at FROM boards WHERE id = ?", (board_id,)
        ).fetchone()
        cols = conn.execute(
            "SELECT id, title, position, wip_limit FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()
        columns_data = []
        for col in cols:
            cards = conn.execute(
                """
                SELECT id, title, details, due_date, label, priority,
                       assigned_to, archived, created_at, position
                FROM cards WHERE column_id = ? ORDER BY position
                """,
                (col["id"],),
            ).fetchall()
            cards_with_comments = []
            for card in cards:
                comments = conn.execute(
                    "SELECT id, username, content, created_at FROM card_comments WHERE card_id = ? ORDER BY created_at",
                    (card["id"],),
                ).fetchall()
                cards_with_comments.append({**dict(card), "comments": [dict(c) for c in comments]})
            columns_data.append({**dict(col), "cards": cards_with_comments})
        return {
            "board": dict(board_row),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "columns": columns_data,
        }
