"""
笔记系统 — 录音转写后的笔记存储、列表、详情
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from database import get_db
from user_auth import get_current_user

router = APIRouter(prefix="/notes")


class CreateNoteRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    transcript: str = Field(default="")
    summary: str = Field(default="")
    key_points: list[str] = Field(default_factory=list)
    markdown: Optional[str] = None  # 文档模式生成的完整 Markdown


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None


@router.get("")
async def list_notes(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """获取用户的笔记列表。"""
    db = get_db()
    result = (
        db.table("notes")
        .select("id, title, summary, key_points, markdown, created_at, updated_at")
        .eq("user_id", current_user["sub"])
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"notes": result.data}


@router.get("/{note_id}")
async def get_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取笔记详情。"""
    db = get_db()
    result = (
        db.table("notes")
        .select("*")
        .eq("id", note_id)
        .eq("user_id", current_user["sub"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Note not found")
    return result.data[0]


@router.post("")
async def create_note(
    req: CreateNoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """创建笔记。"""
    db = get_db()
    row: dict = {
        "user_id": current_user["sub"],
        "title": req.title,
        "transcript": req.transcript,
        "summary": req.summary,
        "key_points": req.key_points,
    }
    if req.markdown is not None:
        row["markdown"] = req.markdown
    result = db.table("notes").insert(row).execute()
    return result.data[0]


@router.patch("/{note_id}")
async def update_note(
    note_id: str,
    req: UpdateNoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新笔记。"""
    db = get_db()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = (
        db.table("notes")
        .update(updates)
        .eq("id", note_id)
        .eq("user_id", current_user["sub"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Note not found")
    return result.data[0]


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
):
    """删除笔记。"""
    db = get_db()
    db.table("notes").delete().eq("id", note_id).eq("user_id", current_user["sub"]).execute()
    return {"status": "deleted"}
