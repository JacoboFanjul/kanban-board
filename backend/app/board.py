from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_auth
from app import db

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class BoardTitleRequest(BaseModel):
    title: str


class RenameColumnRequest(BaseModel):
    title: str


class CreateColumnRequest(BaseModel):
    title: str


class MoveColumnRequest(BaseModel):
    position: int


class CreateCardRequest(BaseModel):
    column_id: str
    title: str
    details: str = ""
    due_date: str | None = None
    label: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class UpdateCardRequest(BaseModel):
    title: str | None = None
    details: str | None = None
    due_date: str | None = None
    label: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class CreateCommentRequest(BaseModel):
    content: str


class WipLimitRequest(BaseModel):
    wip_limit: int | None = None


class MoveCardRequest(BaseModel):
    column_id: str
    position: int


# ---------------------------------------------------------------------------
# Board routes
# ---------------------------------------------------------------------------

@router.get("/boards")
def list_boards(username: Annotated[str, Depends(require_auth)]):
    return db.list_boards(username)


@router.post("/boards", status_code=201)
def create_board(
    body: BoardTitleRequest,
    username: Annotated[str, Depends(require_auth)],
):
    return db.create_board(username, body.title)


@router.get("/boards/{board_id}")
def get_board_by_id(
    board_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    board = db.get_board(username, board_id)
    if not board.get("id"):
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@router.put("/boards/{board_id}")
def rename_board(
    board_id: str,
    body: BoardTitleRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.rename_board(username, board_id, body.title):
        raise HTTPException(status_code=404, detail="Board not found")
    return {"ok": True}


@router.delete("/boards/{board_id}", status_code=204)
def delete_board(
    board_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.delete_board(username, board_id):
        raise HTTPException(status_code=404, detail="Board not found")


# ---------------------------------------------------------------------------
# Backward-compat: GET /api/board (returns first board)
# ---------------------------------------------------------------------------

@router.get("/board")
def get_board(username: Annotated[str, Depends(require_auth)]):
    return db.get_board(username)


# ---------------------------------------------------------------------------
# Column routes
# ---------------------------------------------------------------------------

@router.post("/boards/{board_id}/columns", status_code=201)
def create_column(
    board_id: str,
    body: CreateColumnRequest,
    username: Annotated[str, Depends(require_auth)],
):
    col = db.create_column(username, board_id, body.title)
    if not col:
        raise HTTPException(status_code=404, detail="Board not found")
    return col


@router.put("/board/columns/{column_id}")
def rename_column(
    column_id: str,
    body: RenameColumnRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.rename_column(username, column_id, body.title):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


@router.delete("/board/columns/{column_id}", status_code=204)
def delete_column(
    column_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.delete_column(username, column_id):
        raise HTTPException(status_code=404, detail="Column not found")


@router.put("/board/columns/{column_id}/position")
def move_column(
    column_id: str,
    body: MoveColumnRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.move_column(username, column_id, body.position):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


@router.put("/board/columns/{column_id}/wip-limit")
def set_wip_limit(
    column_id: str,
    body: WipLimitRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.set_column_wip_limit(username, column_id, body.wip_limit):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Card routes
# ---------------------------------------------------------------------------

@router.get("/boards/{board_id}/search")
def search_cards(
    board_id: str,
    username: Annotated[str, Depends(require_auth)],
    q: str = "",
    label: str = "",
    priority: str = "",
):
    return db.search_cards(username, board_id, q, label, priority)


@router.get("/boards/{board_id}/archived")
def get_archived_cards(
    board_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    return db.get_archived_cards(username, board_id)


@router.post("/board/cards", status_code=201)
def create_card(
    body: CreateCardRequest,
    username: Annotated[str, Depends(require_auth)],
):
    card = db.create_card(
        username, body.column_id, body.title, body.details,
        body.due_date, body.label, body.priority, body.assigned_to,
    )
    if not card:
        raise HTTPException(status_code=404, detail="Column not found")
    return card


@router.put("/board/cards/{card_id}")
def update_card(
    card_id: str,
    body: UpdateCardRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.update_card(
        username, card_id, body.title, body.details,
        body.due_date, body.label, body.priority, body.assigned_to,
    ):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


@router.post("/board/cards/{card_id}/archive", status_code=200)
def archive_card(
    card_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.archive_card(username, card_id):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


@router.post("/board/cards/{card_id}/unarchive", status_code=200)
def unarchive_card(
    card_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.unarchive_card(username, card_id):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Card comments
# ---------------------------------------------------------------------------

@router.get("/board/cards/{card_id}/comments")
def get_comments(
    card_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    return db.get_card_comments(username, card_id)


@router.post("/board/cards/{card_id}/comments", status_code=201)
def create_comment(
    card_id: str,
    body: CreateCommentRequest,
    username: Annotated[str, Depends(require_auth)],
):
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Comment content cannot be empty")
    comment = db.create_comment(username, card_id, body.content.strip())
    if not comment:
        raise HTTPException(status_code=404, detail="Card not found")
    return comment


@router.delete("/board/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    if not db.delete_comment(username, comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")


# ---------------------------------------------------------------------------
# Board export
# ---------------------------------------------------------------------------

@router.get("/boards/{board_id}/export")
def export_board(
    board_id: str,
    username: Annotated[str, Depends(require_auth)],
):
    data = db.export_board(username, board_id)
    if not data:
        raise HTTPException(status_code=404, detail="Board not found")
    return data


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
