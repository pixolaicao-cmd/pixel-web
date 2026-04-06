"""
对话历史 — 保存和查询
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from database import get_db
from user_auth import get_current_user

router = APIRouter(prefix="/conversations")


class SaveMessageRequest(BaseModel):
    role: str = Field(..., pattern="^(user|pixel)$")
    content: str = Field(..., min_length=1, max_length=10000)


@router.get("")
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """获取用户的对话历史（最近 N 条）。"""
    db = get_db()
    result = (
        db.table("conversations")
        .select("*")
        .eq("user_id", current_user["sub"])
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"messages": list(reversed(result.data))}


@router.post("")
async def save_message(
    req: SaveMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """保存一条对话消息。"""
    db = get_db()
    result = db.table("conversations").insert({
        "user_id": current_user["sub"],
        "role": req.role,
        "content": req.content,
    }).execute()
    return result.data[0]


@router.delete("")
async def clear_conversations(
    current_user: dict = Depends(get_current_user),
):
    """清空用户的对话历史。"""
    db = get_db()
    db.table("conversations").delete().eq("user_id", current_user["sub"]).execute()
    return {"status": "cleared"}
