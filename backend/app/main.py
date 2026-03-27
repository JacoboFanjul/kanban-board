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

app = FastAPI()


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def login(body: LoginRequest):
    username = validate_credentials(body.username, body.password)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_session(username)}


@app.post("/api/logout")
def logout(token: Annotated[str, Depends(require_token)]):
    delete_session(token)
    return {"ok": True}


@app.get("/api/me")
def me(current_user: Annotated[str, Depends(require_auth)]):
    return {"username": current_user}


static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
