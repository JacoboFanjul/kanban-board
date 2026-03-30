# Project Plan

## Part 1: Planning and Documentation

Enrich this document with detailed substeps, checklists, tests, and success criteria.
Create an AGENTS.md inside the frontend directory describing the existing code.
Get user approval before proceeding.

- [x] Explore existing frontend codebase
- [x] Write detailed plan for all parts
- [x] Create frontend/AGENTS.md
- [x] User approves plan

### Success Criteria
- PLAN.md has actionable checklists for every part
- frontend/AGENTS.md accurately describes the codebase
- User has reviewed and approved

---

## Part 2: Frontend Cleanup

Verify the frontend is clean of any AI chat code or unused features.
The AGENTS.md reference mentions AI chat removal, but exploration confirmed no AI chat
code exists. This step verifies that and ensures a clean baseline.

- [x] Grep frontend for any chat-related code, AI imports, or unused dependencies
- [x] Remove any dead code or unused imports found
- [x] Run existing frontend tests to confirm nothing is broken
- [x] Verify all tests pass (unit + e2e)

### Tests
- `npm run test:unit` passes
- `npm run test:e2e` passes
- No chat-related code exists in any frontend file

### Success Criteria
- Frontend is confirmed clean with no dead code
- All existing tests pass on the clean baseline

---

## Part 3: Scaffolding

Set up Docker infrastructure, FastAPI backend in backend/, and start/stop scripts
in scripts/. Serve example static HTML and expose a test API endpoint.

- [x] Create backend/pyproject.toml with FastAPI, uvicorn dependencies (managed by uv)
- [x] Create backend/app/main.py with FastAPI app
- [x] Add GET / that serves a static "Hello World" HTML page
- [x] Add GET /api/health that returns `{"status": "ok"}`
- [x] Create Dockerfile at project root
  - Python base image
  - Install uv, then use uv to install backend dependencies
  - Copy backend code
  - Expose port 8000
  - CMD: uvicorn
- [x] Create docker-compose.yml at project root
  - Mount a local volume (./data/) to persist SQLite database across restarts
  - Port mapping 8000:8000
- [x] Create scripts/start.sh (Linux) -- builds and starts container
- [x] Create scripts/stop.sh (Linux) -- stops container
- [x] Make scripts executable
- [x] Build and run container, verify it works

### Tests
- `docker-compose up --build` succeeds
- `curl http://localhost:8000/` returns HTML with "Hello World"
- `curl http://localhost:8000/api/health` returns `{"status": "ok"}`
- `scripts/start.sh` builds and starts the container
- `scripts/stop.sh` stops the container
- Container restarts preserve the ./data/ directory

### Success Criteria
- Docker container runs FastAPI serving static HTML and a health API endpoint
- Start/stop scripts work on Linux
- Volume mount for ./data/ is confirmed working

---

## Part 4: Add in Frontend

Build the Next.js frontend as a static export and serve it from FastAPI at /.
The demo Kanban board should display at http://localhost:8000/.

- [x] Configure next.config.ts for static export (`output: 'export'`)
- [x] Add a build step in the Dockerfile: install Node, npm install, npm run build
- [x] Copy the static export output into a directory the backend can serve
- [x] Update FastAPI to serve the static frontend files at / (using StaticFiles mount)
- [x] Ensure API routes under /api/ still work alongside the static frontend
- [x] Build and run container, verify Kanban board loads at /
- [x] Write backend integration test: GET / returns HTML containing expected content
- [x] Write backend integration test: GET /api/health still returns ok

### Tests
- Backend integration tests (pytest + httpx): static files served, API routes work
- Frontend unit tests still pass (`npm run test:unit`)
- Manual verification: Kanban board renders at http://localhost:8000/

### Success Criteria
- Kanban board displays at http://localhost:8000/ inside Docker
- API endpoints remain accessible under /api/
- All tests pass

---

## Part 5: Add Authentication

Add a login screen. Users must authenticate with hardcoded credentials ("user" /
"password") via the backend API to access the Kanban board. Session-based auth
using a token/cookie.

- [x] Backend: POST /api/login endpoint (accepts username + password, returns session token)
- [x] Backend: POST /api/logout endpoint (invalidates session)
- [x] Backend: GET /api/me endpoint (returns current user if authenticated, 401 otherwise)
- [x] Backend: auth middleware/dependency that protects /api/ routes (except login)
- [x] Backend: session storage (in-memory dict for MVP, keyed by token)
- [x] Backend unit tests for all auth endpoints (valid login, invalid login, logout, protected routes)
- [x] Frontend: login page component with username/password form
- [x] Frontend: auth state management (store token, redirect to login if unauthenticated)
- [x] Frontend: logout button on the Kanban board
- [x] Frontend: styling matches the color scheme (purple submit button, navy headings)
- [x] Frontend unit tests for login component
- [x] End-to-end: rebuild and test in Docker

### Tests
- pytest: login with correct creds returns 200 + token
- pytest: login with wrong creds returns 401
- pytest: accessing /api/me without token returns 401
- pytest: accessing /api/me with valid token returns user info
- pytest: logout invalidates the token
- Frontend unit tests: login form renders, submits, handles errors
- E2E in Docker: full login -> board -> logout flow

### Success Criteria
- Cannot access Kanban board without logging in
- "user" / "password" grants access
- Logout returns to login screen
- All tests pass

---

## Part 6: Database Schema

Design the SQLite database schema for the Kanban board. Document it and get
user sign off before implementation.

- [x] Design schema supporting: users, boards, columns, cards
- [x] Schema supports multiple users (future-proof) but MVP uses 1 user
- [x] Schema supports 1 board per user (MVP)
- [x] Columns have an order field for positioning
- [x] Cards have an order field for positioning within a column
- [x] Save schema as docs/database-schema.json
- [x] Document the schema and design decisions in docs/DATABASE.md
- [x] Get user approval

### Success Criteria
- Schema is clear, minimal, and supports the Kanban data model
- User has approved the schema

---

## Part 7: Backend API

Add API routes to CRUD the Kanban data for the authenticated user. SQLite
database is created automatically if it does not exist.

- [x] Database initialization: create tables from schema on app startup if DB doesn't exist
- [x] Seed the default user ("user") and default board with initial columns on first run
- [x] GET /api/board -- returns the user's board (columns + cards, ordered)
- [x] PUT /api/board/columns/{id} -- rename a column
- [x] POST /api/board/cards -- create a card in a column
- [x] DELETE /api/board/cards/{id} -- delete a card
- [x] PUT /api/board/cards/{id}/move -- move a card (reorder within column or across columns)
- [x] All endpoints require authentication
- [x] Backend unit tests for every endpoint (pytest + httpx)
- [x] Test database auto-creation from scratch
- [x] Test concurrent operations don't corrupt data

### Tests
- pytest: GET /api/board returns correct structure
- pytest: create card, verify it appears in GET /api/board
- pytest: delete card, verify it's gone
- pytest: rename column, verify the change
- pytest: move card within column, verify order
- pytest: move card across columns, verify both columns update
- pytest: all endpoints return 401 without auth
- pytest: DB is created fresh if missing

### Success Criteria
- Full CRUD for Kanban data via API
- Database auto-creates on first run
- All tests pass
- Data persists across container restarts (volume mount)

---

## Part 8: Frontend + Backend Integration

Connect the frontend to the backend API so the Kanban board is fully persistent.

- [ ] Replace local React state with API calls (fetch board on load, mutate via API)
- [ ] Board data loads from GET /api/board on mount
- [ ] Column rename calls PUT /api/board/columns/{id}
- [ ] Add card calls POST /api/board/cards
- [ ] Delete card calls DELETE /api/board/cards/{id}
- [ ] Drag and drop calls PUT /api/board/cards/{id}/move
- [ ] Handle loading states and API errors gracefully
- [ ] Auth token sent with every API request
- [ ] Redirect to login on 401 responses
- [ ] Update frontend unit tests to mock API calls
- [ ] Update or add E2E tests for the full flow
- [ ] Full rebuild and test in Docker

### Tests
- Frontend unit tests: components render with mocked API data
- Frontend unit tests: user actions trigger correct API calls
- E2E in Docker: login -> view board -> add card -> move card -> rename column -> delete card -> logout -> login again -> data persists
- E2E: refresh page, verify data persists

### Success Criteria
- Kanban board loads real data from the backend
- All user actions (add, delete, move, rename) persist to the database
- Data survives page refreshes and container restarts
- Login/logout flow works end to end
- All tests pass