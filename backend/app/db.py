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


def init_db() -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id         TEXT PRIMARY KEY,
            username   TEXT NOT NULL REFERENCES users(username),
            created_at TEXT NOT NULL,
            UNIQUE(username)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id       TEXT PRIMARY KEY,
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            title    TEXT NOT NULL,
            position INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id        TEXT PRIMARY KEY,
            column_id TEXT NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
            title     TEXT NOT NULL,
            details   TEXT NOT NULL DEFAULT '',
            position  INTEGER NOT NULL
        )
    """)
    conn.commit()

    # Seed only if no users exist yet
    if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        conn.close()
        return

    board_id = secrets.token_hex(8)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT INTO users VALUES (?, ?)", ("user", hash_password("password")))
    conn.execute("INSERT INTO boards VALUES (?, ?, ?)", (board_id, "user", now))
    for col_id, title, pos in _SEED_COLUMNS:
        conn.execute("INSERT INTO columns VALUES (?, ?, ?, ?)", (col_id, board_id, title, pos))
    for card_id, col_id, title, details, pos in _SEED_CARDS:
        conn.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?)", (card_id, col_id, title, details, pos))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_password_hash(username: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        return row["password_hash"] if row else None


def get_board_id(conn: sqlite3.Connection, username: str) -> str | None:
    row = conn.execute("SELECT id FROM boards WHERE username = ?", (username,)).fetchone()
    return row["id"] if row else None


def get_board(username: str) -> dict:
    with get_conn() as conn:
        board_id = get_board_id(conn, username)
        if not board_id:
            return {"columns": []}
        cols = conn.execute(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()
        result = []
        for col in cols:
            cards = conn.execute(
                "SELECT id, title, details FROM cards WHERE column_id = ? ORDER BY position",
                (col["id"],),
            ).fetchall()
            result.append({
                "id": col["id"],
                "title": col["title"],
                "cards": [dict(c) for c in cards],
            })
        return {"columns": result}


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def rename_column(username: str, column_id: str, title: str) -> bool:
    with get_conn() as conn:
        board_id = get_board_id(conn, username)
        if not board_id:
            return False
        result = conn.execute(
            "UPDATE columns SET title = ? WHERE id = ? AND board_id = ?",
            (title, column_id, board_id),
        )
        return result.rowcount == 1


def create_card(username: str, column_id: str, title: str, details: str) -> dict | None:
    with get_conn() as conn:
        board_id = get_board_id(conn, username)
        if not board_id:
            return None
        col = conn.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (column_id, board_id),
        ).fetchone()
        if not col:
            return None
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM cards WHERE column_id = ?",
            (column_id,),
        ).fetchone()[0]
        card_id = secrets.token_hex(8)
        position = max_pos + 1
        conn.execute(
            "INSERT INTO cards VALUES (?, ?, ?, ?, ?)",
            (card_id, column_id, title, details, position),
        )
        return {"id": card_id, "title": title, "details": details}


def delete_card(username: str, card_id: str) -> bool:
    with get_conn() as conn:
        board_id = get_board_id(conn, username)
        if not board_id:
            return False
        # Verify the card belongs to this user's board via its column
        row = conn.execute(
            """
            SELECT cards.id, cards.column_id, cards.position
            FROM cards
            JOIN columns ON cards.column_id = columns.id
            WHERE cards.id = ? AND columns.board_id = ?
            """,
            (card_id, board_id),
        ).fetchone()
        if not row:
            return False
        col_id = row["column_id"]
        position = row["position"]
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        # Close the gap in the source column
        conn.execute(
            "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
            (col_id, position),
        )
        return True


def move_card(username: str, card_id: str, target_column_id: str, target_position: int) -> bool:
    with get_conn() as conn:
        board_id = get_board_id(conn, username)
        if not board_id:
            return False
        # Verify card belongs to this user's board
        row = conn.execute(
            """
            SELECT cards.id, cards.column_id, cards.position
            FROM cards
            JOIN columns ON cards.column_id = columns.id
            WHERE cards.id = ? AND columns.board_id = ?
            """,
            (card_id, board_id),
        ).fetchone()
        if not row:
            return False
        # Verify target column belongs to this user's board
        target_col = conn.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (target_column_id, board_id),
        ).fetchone()
        if not target_col:
            return False

        src_col_id = row["column_id"]
        src_pos = row["position"]

        # Clamp target_position to valid range
        col_card_count = conn.execute(
            "SELECT COUNT(*) FROM cards WHERE column_id = ?",
            (target_column_id,),
        ).fetchone()[0]
        # If moving within the same column, the count includes the card itself
        if src_col_id == target_column_id:
            max_pos = col_card_count - 1
        else:
            max_pos = col_card_count  # one slot will open up after removal
        target_position = max(0, min(target_position, max_pos))

        if src_col_id == target_column_id and src_pos == target_position:
            return True  # no-op

        if src_col_id == target_column_id:
            # Moving within the same column
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
            # Cross-column move: remove from source, insert into target
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
