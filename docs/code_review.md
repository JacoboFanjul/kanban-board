# Code Review

Reviewed on 2026-06-02 against branch `jjf` (full diff from `main`).  
Effort: high — 7 independent finder angles, 1-vote adversarial verification per candidate.

---

## Findings

### 1. Hardcoded credentials; `users` table is never consulted for auth

**File:** `backend/app/auth.py:6`  
**Severity:** High (security)

`validate_credentials` compares against two hardcoded module-level constants (`_USER = "user"`, `_PASSWORD = "password"`). It never reads the database. `init_db()` seeds the `users` table with an empty string for `password_hash`, so the column name implies hashing that never happens and the value stored is never read.

**Impact:** The password can only be changed with a code redeploy. Any future code that tries to do DB-based auth (add users, change password) will silently have no effect.

**Fix:** Move credentials into the DB with a real hash (e.g. `bcrypt`/`argon2`), and update `validate_credentials` to query `users` and verify the hash.

---

### 2. Session store has no expiry and no size cap

**File:** `backend/app/auth.py:10`  
**Severity:** High (security)

`_sessions: dict[str, str] = {}` grows without bound. Each call to `create_session()` adds a token that is valid until an explicit logout call uses that exact token. A user who logs in N times without logging out accumulates N permanently valid tokens.

**Impact:** Stolen tokens are valid forever. A buggy client that retries login in a loop will exhaust server memory.

**Fix:** Record a creation timestamp alongside each token and reject tokens older than a configurable TTL (e.g. 24 h). Also invalidate all tokens for a user on password change.

---

### 3. Optimistic mutations silently swallow non-401 errors with no rollback

**File:** `frontend/src/components/KanbanBoard.tsx:76` (also `:100`, `:127`)  
**Severity:** Medium (correctness)

All three mutation handlers (drag/move at line 76, rename-commit at line 100, delete at line 127) mutate client state before the API call and then fire the API call as fire-and-forget. Each `.catch` handler only acts on `ApiError(401)`; every other failure (500, network error, 404) is silently discarded.

```ts
setBoard(...)  // optimistic — happens first
apiMoveCard(...).catch((err: unknown) => {
  if (err instanceof ApiError && err.status === 401) handle401();
  // 500 / network error: swallowed, no rollback
});
```

**Impact:** After a network failure or server error, the UI shows the mutated board (card moved/deleted/renamed) while the server retains the original state. A page refresh silently reverts the change with no indication to the user.

**Fix:** Capture the previous board state before each mutation and revert to it on any non-401 error:

```ts
const prevBoard = board;
setBoard(next);
apiMoveCard(...).catch((err) => {
  if (err instanceof ApiError && err.status === 401) handle401();
  else setBoard(prevBoard);
});
```

---

### 4. `handleLogout` does not catch network errors; cleanup is skipped on failure

**File:** `frontend/src/app/page.tsx:31`  
**Severity:** Medium (correctness)

```ts
const handleLogout = async () => {
    if (token) await apiLogout(token);  // can throw on network error
    removeToken();                       // skipped if above throws
    setToken(null);                      // skipped if above throws
};
```

`apiLogout` calls `fetch()` directly with no error handling. `fetch()` rejects on DNS failure, connection refused, or timeout. Since `handleLogout` has no `try/catch`, a network error propagates out and the two cleanup lines are never reached.

**Impact:** The user clicks "Sign out", nothing visible changes, and they appear stuck on the board.

**Fix:** Wrap in try/catch (or try/finally) so cleanup always runs:

```ts
const handleLogout = async () => {
    try {
      if (token) await apiLogout(token);
    } finally {
      removeToken();
      setToken(null);
    }
};
```

---

### 5. Non-401 errors from `apiGetBoard` leave the board stuck on "Loading…" forever

**File:** `frontend/src/components/KanbanBoard.tsx:54`  
**Severity:** Medium (UX / correctness)

```ts
apiGetBoard(token)
  .then((data) => setBoard(normalizeBoard(data)))
  .catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) handle401();
    // 500 / network error: swallowed, board stays null
  });
```

Any failure other than a 401 is silently discarded. `board` remains `null`, and the component renders a "Loading…" spinner indefinitely with no error message and no retry affordance.

**Fix:** Add an error state and display a message (plus a retry button) when loading fails.

---

### 6. `init_db()` opens a raw connection without `try/finally`; leaks on exception

**File:** `backend/app/db.py:48`  
**Severity:** Low (reliability)

`init_db()` calls `sqlite3.connect()` directly and manually calls `conn.close()` at lines 85 and 97. There is no `try/finally` around the connection. If an exception is raised during the seed `INSERT` statements (e.g. `OperationalError: disk full`), `conn.close()` is never called, leaking the file descriptor.

This is inconsistent with the rest of the module, which uses the `get_conn()` context manager (which guarantees `close()` in a `finally` block).

**Fix:** Refactor `init_db` to use `get_conn()` for the seed block, or wrap the raw connection in `try/finally: conn.close()`.

---

### 7. No `min_length` / `max_length` validation on request model string fields

**File:** `backend/app/board.py:12`  
**Severity:** Low (correctness / security)

`RenameColumnRequest`, `CreateCardRequest`, and `MoveCardRequest` declare bare `str` fields with no Pydantic `Field` constraints:

```python
class RenameColumnRequest(BaseModel):
    title: str   # accepts "", and arbitrarily long strings

class CreateCardRequest(BaseModel):
    title: str
    details: str = ""
```

Two concrete consequences:
- **Empty column title:** `KanbanColumn.tsx` fires `onRenameCommit` on every `blur` event with whatever is in the input, including an empty string. There is no client-side guard and no server-side guard, so a column can be persisted with a blank title.
- **Unbounded payload:** A direct API call can send megabyte-sized strings as card titles or details. SQLite stores them without complaint, inflating every subsequent board load.

**Fix:**

```python
from pydantic import Field

class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)

class CreateCardRequest(BaseModel):
    column_id: str
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)
```

Also add a client-side guard in `KanbanColumn.tsx` `onBlur` to skip the commit when the trimmed title is empty.

---

### 8. N+1 query pattern in `get_board`

**File:** `backend/app/db.py:119`  
**Severity:** Low (efficiency)

```python
cols = conn.execute("SELECT id, title FROM columns WHERE board_id = ?", ...).fetchall()
for col in cols:
    cards = conn.execute(
        "SELECT id, title, details FROM cards WHERE column_id = ? ORDER BY position",
        (col["id"],),
    ).fetchall()
```

A board with N columns issues N+1 sequential queries per `GET /api/board` request. With 5 columns that is 6 queries; if column count grows, query count scales linearly.

**Fix:** Replace with a single JOIN or two queries (fetch all columns, then fetch all cards for the board in one `WHERE column_id IN (...)` query) and group in Python.

---

## Summary

| # | File | Line | Category | Severity |
|---|------|------|----------|----------|
| 1 | `backend/app/auth.py` | 6 | Security | High |
| 2 | `backend/app/auth.py` | 10 | Security | High |
| 3 | `frontend/src/components/KanbanBoard.tsx` | 76, 100, 127 | Correctness | Medium |
| 4 | `frontend/src/app/page.tsx` | 31 | Correctness | Medium |
| 5 | `frontend/src/components/KanbanBoard.tsx` | 54 | UX/Correctness | Medium |
| 6 | `backend/app/db.py` | 48 | Reliability | Low |
| 7 | `backend/app/board.py` | 12 | Correctness/Security | Low |
| 8 | `backend/app/db.py` | 119 | Efficiency | Low |
