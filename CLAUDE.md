# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack Kanban board MVP. Frontend: Next.js 16 (static export) + React 19 + TypeScript + Tailwind + @dnd-kit. Backend: Python FastAPI + SQLite. Served as a single Docker container where FastAPI serves the pre-built static frontend.

## Commands

### Frontend
```bash
cd frontend
npm install
npm run dev          # dev server at http://localhost:3000
npm run build        # static export to out/
npm run lint         # ESLint
npm run test:unit    # vitest
npm run test:e2e     # Playwright
npm run test:all     # unit + e2e
```

### Backend
```bash
cd backend
uv pip install -e ".[test]"          # install with test deps
pytest                                # run all tests
python -m uvicorn app.main:app --reload  # dev server
```

### Docker (full stack)
```bash
scripts/start.sh   # docker-compose up --build -d → http://localhost:8000
scripts/stop.sh    # docker-compose down
```

## Architecture

**Request flow:** Browser → FastAPI (`:8000`) → static files served from `./static` (built frontend). API routes (`/api/*`) are handled by FastAPI; all other routes serve the Next.js static export.

**Auth:** Login via `POST /api/login`, receives a session token stored in `localStorage`. All subsequent API calls send `Authorization: Bearer {token}`. Sessions are in-memory (dict in `app/auth.py`) — they reset on server restart.

**Data persistence:** SQLite at `./data/pm.db` (volume-mounted in Docker). Database auto-initializes on startup with seed data: one user (`user`/`password`), one board, five columns (Backlog → Done), eight sample cards.

**Backend modules:**
- `app/main.py` — app init, auth endpoints (`/api/login`, `/api/logout`, `/api/me`), static file serving
- `app/auth.py` — session token management, credential validation
- `app/db.py` — all SQLite queries, schema init, CRUD for boards/columns/cards
- `app/board.py` — APIRouter for board endpoints: `GET /api/board`, `PUT /api/board/columns/{id}`, `POST /api/board/cards`, `DELETE /api/board/cards/{id}`, `PUT /api/board/cards/{id}/move`

**Frontend modules:**
- `src/lib/api.ts` — all API client functions and token storage helpers
- `src/lib/kanban.ts` — board data types and local move logic
- `src/components/KanbanBoard.tsx` — main board with @dnd-kit drag-and-drop, API mutation calls
- `src/app/page.tsx` — root page, auth state, token management

## Database Schema

```
users(username PK, password_hash)
boards(id PK, username FK, created_at)
columns(id PK, board_id FK, title, position)
cards(id PK, column_id FK, title, details, position)
```

Foreign keys enforced via `PRAGMA foreign_keys = ON`. Card/column order tracked by integer `position` field.

## Color Scheme

All UI must use: Yellow `#ecad0a`, Blue `#209dd7`, Purple `#753991`, Navy `#032147`, Gray `#888888`. Defined as CSS variables in `src/app/layout.tsx`.
