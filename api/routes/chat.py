"""
POST /chat — AI 对话
支持 Grok / Claude 双引擎，注入 Pixel 人格。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import verify_token
from user_auth import get_current_user_optional
from config import PIXEL_SYSTEM_PROMPT, XAI_API_KEY, ANTHROPIC_API_KEY, AI_ENGINE, OLLAMA_BASE_URL
from ai_client import chat_completion, get_engine_name

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    user_id: str = Field(default="default")


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    engine: str


def _fetch_memories(user_id: str, query: str, limit: int = 5) -> str:
    """向量搜索相关记忆，返回注入 prompt 的文字。"""
    try:
        from routes.memories import embed
        from database import get_db
        embedding = embed(query)
        db = get_db()
        result = db.rpc("match_memories", {
            "query_embedding": embedding,
            "match_user_id": user_id,
            "match_count": limit,
        }).execute()
        memories = result.data or []
        if not memories:
            return ""
        lines = "\n".join(f"- {m['content']}" for m in memories)
        return f"\n\n【关于这个用户你记得的事情】\n{lines}"
    except Exception:
        return ""


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    _: None = Depends(verify_token),
    current_user: dict | None = Depends(get_current_user_optional),
):
    """接收用户文字，注入相关记忆后返回 Pixel 的回复。"""
    if AI_ENGINE == "grok" and not XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY not configured")
    if AI_ENGINE == "claude" and not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    if AI_ENGINE == "ollama" and not OLLAMA_BASE_URL:
        raise HTTPException(status_code=500, detail="OLLAMA_BASE_URL not configured")

    # 注入记忆
    memory_context = ""
    if current_user:
        memory_context = _fetch_memories(current_user["sub"], req.message)

    system_prompt = PIXEL_SYSTEM_PROMPT + memory_context

    reply_text = await chat_completion(
        system_prompt=system_prompt,
        user_message=req.message,
        max_tokens=512,
    )

    return ChatResponse(reply=reply_text, user_id=req.user_id, engine=get_engine_name())
