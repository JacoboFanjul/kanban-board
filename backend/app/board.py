from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_auth
from app import db

router = APIRouter(prefix="/api")


class RenameColumnRequest(BaseModel):
    title: str


class CreateCardRequest(BaseModel):
    column_id: str
    title: str
    details: str = ""


class MoveCardRequest(BaseModel):
    column_id: str
    position: int


@router.get("/board")
def get_board(username: Annotated[str, Depends(require_auth)]):
    return db.get_board(username)


@router.put("/board/columns/{column_id}")
def rename_column(
    column_id: str,
    body: RenameColumnRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.rename_column(username, column_id, body.title):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


@router.post("/board/cards", status_code=201)
def create_card(
    body: CreateCardRequest,
    username: Annotated[str, Depends(require_auth)],
):
    card = db.create_card(username, body.column_id, body.title, body.details)
    if not card:
        raise HTTPException(status_code=404, detail="Column not found")
    return card


@router.delete("/board/cards/{card_id}", status_code=204)
def delete_card(
    card_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.delete_card(username, card_id):
        raise HTTPException(status_code=404, detail="Card not found")


@router.put("/board/cards/{card_id}/move")
def move_card(
    card_id: str,
    body: MoveCardRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.move_card(username, card_id, body.column_id, body.position):
        raise HTTPException(status_code=404, detail="Card or column not found")
    return {"ok": True}
