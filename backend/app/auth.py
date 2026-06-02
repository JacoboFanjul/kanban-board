import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Header, HTTPException

from app.security import verify_password
from app import db

_SESSION_TTL = timedelta(hours=24)

# session store: token -> (username, created_at)
_sessions: dict[str, tuple[str, datetime]] = {}


def validate_credentials(username: str, password: str) -> str | None:
    stored_hash = db.get_password_hash(username)
    if stored_hash is None:
        return None
    return username if verify_password(password, stored_hash) else None


def create_session(username: str) -> str:
    token = secrets.token_hex(32)
    _sessions[token] = (username, datetime.now(timezone.utc))
    return token


def _get_session_username(token: str) -> str | None:
    entry = _sessions.get(token)
    if not entry:
        return None
    username, created_at = entry
    if datetime.now(timezone.utc) - created_at > _SESSION_TTL:
        _sessions.pop(token, None)
        return None
    return username


def _parse_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return authorization.removeprefix("Bearer ")


def require_auth(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: returns username of the authenticated user."""
    token = _parse_bearer(authorization)
    username = _get_session_username(token)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


def require_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: returns the validated raw token (used for logout)."""
    token = _parse_bearer(authorization)
    if not _get_session_username(token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def delete_session(token: str) -> None:
    _sessions.pop(token, None)
