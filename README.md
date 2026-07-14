# 📋 Kanban Studio

Full-stack Kanban board MVP. Multi-board support with columns, cards, drag-and-drop reordering, priorities, comments, assignment, archiving, search/filter, WIP limits, and board export. 🚀

- **Frontend:** ⚛️ Next.js 16 (static export), React 19, TypeScript, Tailwind, @dnd-kit
- **Backend:** 🐍 Python FastAPI, SQLite
- **Deployment:** 🐳 Single Docker container — FastAPI serves the pre-built static frontend

## 🏁 Quick start (Docker)

```bash
scripts/start.sh   # docker-compose up --build -d
```

App available at http://localhost:8000. Log in with `user` / `password`.

```bash
scripts/stop.sh    # docker-compose down
```

## 💻 Local development

### Backend

```bash
cd backend
uv pip install -e ".[test]"
python -m uvicorn app.main:app --reload   # http://localhost:8000
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run build        # static export to out/
npm run lint
npm run test:unit    # vitest
npm run test:e2e     # Playwright
npm run test:all     # unit + e2e
```

## 🏗️ Architecture

Browser → FastAPI (`:8000`) → static files from `./static` (built frontend). Routes under `/api/*` are handled by FastAPI; all other routes serve the Next.js static export.

**Auth:** `POST /api/login` returns a session token stored in `localStorage`; subsequent requests send `Authorization: Bearer {token}`. Sessions are in-memory and reset on server restart.

**Data:** SQLite at `./data/pm.db` (volume-mounted in Docker). The database auto-initializes on first run with seed data.

See [`CLAUDE.md`](CLAUDE.md) for detailed module layout and the database schema, and [`docs/`](docs/) for design/planning notes.

## 📁 Project structure

```
backend/    FastAPI app, SQLite access, tests
frontend/   Next.js app, components, unit + e2e tests
scripts/    start.sh / stop.sh for the Docker stack
docs/       schema and planning docs
```
