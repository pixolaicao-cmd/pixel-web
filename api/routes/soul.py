"""
Pixel Soul — 用户自定义 Pixel 的人格设置
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from database import get_db
from user_auth import get_current_user

router = APIRouter(prefix="/soul")

DEFAULT_SOUL = {
    "pixel_name": "Pixel",
    "personality": "friendly",
    "language": "auto",
    "voice_style": "warm",
    "custom_prompt": "",
}


@router.get("")
async def get_soul(current_user: dict = Depends(get_current_user)):
    """获取用户的 Pixel Soul 设置。"""
    db = get_db()
    result = (
        db.table("soul_settings")
        .select("*")
        .eq("user_id", current_user["sub"])
        .execute()
    )
    if not result.data:
        return DEFAULT_SOUL
    return result.data[0]


class UpdateSoulRequest(BaseModel):
    pixel_name: Optional[str] = Field(default=None, max_length=50)
    personality: Optional[str] = Field(default=None, pattern="^(friendly|professional|playful|calm)$")
    language: Optional[str] = Field(default=None, pattern="^(auto|zh|en|no)$")
    voice_style: Optional[str] = Field(default=None, pattern="^(warm|energetic|calm|serious)$")
    custom_prompt: Optional[str] = Field(default=None, max_length=500)


def _sanitize_custom_prompt(text: str) -> str:
    """Strip characters that could enable prompt injection."""
    return text.replace("`", "").replace("<", "").replace(">", "")


@router.put("")
async def update_soul(
    req: UpdateSoulRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新 Pixel Soul 设置。"""
    db = get_db()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if "custom_prompt" in updates and updates["custom_prompt"]:
        updates["custom_prompt"] = _sanitize_custom_prompt(updates["custom_prompt"])
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    # Upsert：存在则更新，不存在则插入
    existing = (
        db.table("soul_settings")
        .select("id")
        .eq("user_id", current_user["sub"])
        .execute()
    )

    if existing.data:
        result = (
            db.table("soul_settings")
            .update(updates)
            .eq("user_id", current_user["sub"])
            .execute()
        )
    else:
        updates["user_id"] = current_user["sub"]
        for k, v in DEFAULT_SOUL.items():
            updates.setdefault(k, v)
        result = db.table("soul_settings").insert(updates).execute()

    return result.data[0]
