# Backend

Python FastAPI app. Manages all API routes and serves the static frontend.

## Stack

- Python 3.12, FastAPI 0.115+, uvicorn (with standard extras)
- uv as package manager (pyproject.toml defines all dependencies)
- SQLite for the database (in later parts)
- pytest + httpx for testing

## Structure

- app/main.py -- FastAPI app instance and route definitions
- app/ -- all application modules live here
- tests/ -- pytest test suite

## Running (inside Docker)

The container runs: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Use scripts/start.sh and scripts/stop.sh to manage the container.
Before building for the first time, run: `docker buildx use default`

## Running tests

Inside the container or with dependencies installed locally (uv pip install .[test]):
```
pytest backend/tests/
```

## Notes

- The `./data/` directory on the host is mounted at `/data` inside the container for SQLite persistence
- pyproject.toml uses hatchling as the build backend so `uv pip install --system .` works in Docker
