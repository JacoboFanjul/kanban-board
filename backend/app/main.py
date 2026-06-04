import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth import (
    create_session,
    delete_session,
    require_auth,
    require_token,
    validate_credentials,
)
from app.board import router as board_router
from app import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(board_router)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def login(body: LoginRequest):
    username = validate_credentials(body.username, body.password)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_session(username)}


@app.post("/api/register", status_code=201)
def register(body: RegisterRequest):
    if not _USERNAME_RE.match(body.username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-32 characters: letters, digits, _ or -",
        )
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if not db.create_user(body.username, body.password, body.email):
        raise HTTPException(status_code=409, detail="Username already taken")
    return {"token": create_session(body.username)}


@app.post("/api/logout")
def logout(token: Annotated[str, Depends(require_token)]):
    delete_session(token)
    return {"ok": True}


@app.get("/api/me")
def me(current_user: Annotated[str, Depends(require_auth)]):
    return {"username": current_user}


@app.put("/api/me/password")
def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[str, Depends(require_auth)],
):
    if not validate_credentials(current_user, body.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    db.update_password(current_user, body.new_password)
    return {"ok": True}


static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
