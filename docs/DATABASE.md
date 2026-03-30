# Database Design

SQLite database stored at `/data/pm.db` inside the container (mounted from `./data/` on the host).

## Tables

### users

| Column        | Type | Constraints   |
|---------------|------|---------------|
| username      | TEXT | PRIMARY KEY   |
| password_hash | TEXT | NOT NULL      |

Stores registered users. For the MVP a single user (`user`) is seeded on first run. The `password_hash` field is included for future multi-user support; auth is currently validated against hardcoded credentials in `app/auth.py`.

### boards

| Column     | Type | Constraints                      |
|------------|------|----------------------------------|
| id         | TEXT | PRIMARY KEY                      |
| username   | TEXT | NOT NULL, REFERENCES users       |
| created_at | TEXT | NOT NULL (ISO-8601 UTC)          |

One board per user, enforced by `UNIQUE(username)`. The MVP creates one board for the seeded user.

### columns

| Column   | Type    | Constraints                            |
|----------|---------|----------------------------------------|
| id       | TEXT    | PRIMARY KEY                            |
| board_id | TEXT    | NOT NULL, REFERENCES boards ON DELETE CASCADE |
| title    | TEXT    | NOT NULL                               |
| position | INTEGER | NOT NULL                               |

Columns belong to a board and are ordered by `position` (0-based). The MVP seeds five columns: Backlog, Discovery, In Progress, Review, Done.

### cards

| Column    | Type    | Constraints                              |
|-----------|---------|------------------------------------------|
| id        | TEXT    | PRIMARY KEY                              |
| column_id | TEXT    | NOT NULL, REFERENCES columns ON DELETE CASCADE |
| title     | TEXT    | NOT NULL                                 |
| details   | TEXT    | NOT NULL, DEFAULT ''                     |
| position  | INTEGER | NOT NULL                                 |

Cards belong to a column and are ordered by `position` (0-based) within that column. Moving a card updates `column_id` and/or `position`.

## Design Decisions

**Text IDs** -- All primary keys are `TEXT` (random hex strings generated at creation). Avoids auto-increment coupling and matches the existing frontend ID format.

**position column** -- Ordering is stored as a dense integer per-column (0, 1, 2, ...). On insert/move, affected rows are renumbered. This is simple and correct for small boards.

**ON DELETE CASCADE** -- Deleting a board cascades to columns; deleting a column cascades to cards. Enabled via `PRAGMA foreign_keys = ON` at connection open.

**password_hash** -- Stored for future use. The MVP seeds it with the bcrypt hash of the hardcoded password. Auth logic in `app/auth.py` still validates hardcoded credentials for now and will be wired to the database in a future part.

**1 board per user** -- Enforced by `UNIQUE(username)` on the boards table. The single-board MVP constraint is in the data, not the schema, making it easy to relax later.

## Initialisation

On application startup, `app/db.py` will:
1. Open `PRAGMA foreign_keys = ON`
2. Run `CREATE TABLE IF NOT EXISTS` for all four tables
3. Seed the default user and board if the users table is empty
