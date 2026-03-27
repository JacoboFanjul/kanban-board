import secrets
from typing import Annotated

from fastapi import Header, HTTPException

_USER = "user"
_PASSWORD = "password"

# In-memory session store: token -> username
_sessions: dict[str, str] = {}


def validate_credentials(username: str, password: str) -> str | None:
    if username == _USER and password == _PASSWORD:
        return username
    return None


def create_session(username: str) -> str:
    token = secrets.token_hex(32)
    _sessions[token] = username
    return token


def _parse_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return authorization.removeprefix("Bearer ")


def require_auth(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: returns username of the authenticated user."""
    token = _parse_bearer(authorization)
    username = _sessions.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


def require_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: returns the validated raw token (used for logout)."""
    token = _parse_bearer(authorization)
    if token not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def delete_session(token: str) -> None:
    _sessions.pop(token, None)
