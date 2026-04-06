"""
UI Routes — 网页前端专用接口
使用 JWT 认证（无需 API Token），自动保存对话历史
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from user_auth import get_current_user
from config import PIXEL_SYSTEM_PROMPT
from ai_client import chat_completion, get_engine_name
import edge_tts
import io
import asyncio
import json

router = APIRouter(prefix="/ui")

VOICE_MAP = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "no": "nb-NO-PernilleNeural",
    "en": "en-US-JennyNeural",
}


class UIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class UISpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    lang: str = Field(default="zh", pattern="^(zh|no|en)$")


class IntentRequest(BaseModel):
    text: str


class IntentResponse(BaseModel):
    action: str
    context: str
    delay_minutes: int
    output_type: str
    translate_to: str
    reply: str


_MEMORY_EXTRACT_PROMPT = """你是记忆提取助手。分析以下对话，提取关于用户的有价值的长期信息（偏好、习惯、身份、目标、重要事实）。
如果有值得记住的内容，返回JSON数组：[{"content": "...", "category": "..."}]
如果没有值得记住的内容，返回空数组：[]
category 可以是：preference（偏好）、identity（身份）、goal（目标）、habit（习惯）、fact（事实）
只提取明确、具体、有价值的信息，不要提取临时性内容。"""

_INTENT_PROMPT = """你是 Pixel AI 的意图解析器。用户对你说了一句话，你要理解他们的意图并返回结构化JSON。

action 选项：
- "record": 只录音记录
- "translate": 只翻译（不保存）
- "record_translate": 录音+翻译
- "summarize": 对当前内容总结
- "stop": 停止当前模式
- "chat": 普通对话（不需要特殊操作）

context 选项：classroom, meeting, conversation, general

返回格式（只返回JSON，不要其他内容）：
{"action":"...","context":"...","delay_minutes":0,"output_type":"...","translate_to":"","reply":"..."}

reply 字段：用中文回应用户，自然友好，确认你理解了他们的意图。"""


def _fetch_memories(user_id: str, query: str) -> str:
    try:
        from routes.memories import embed
        from database import get_db
        embedding = embed(query)
        db = get_db()
        result = db.rpc("match_memories", {
            "query_embedding": embedding,
            "match_user_id": user_id,
            "match_count": 5,
        }).execute()
        memories = result.data or []
        if not memories:
            return ""
        lines = "\n".join(f"- {m['content']}" for m in memories)
        return f"\n\n【关于这个用户你记得的事情】\n{lines}"
    except Exception:
        return ""


async def _extract_and_save_memories(user_id: str, user_message: str, reply_text: str):
    """后台任务：从对话中提取记忆并保存。"""
    try:
        conversation = f"用户：{user_message}\nPixel：{reply_text}"
        raw = await asyncio.to_thread(
            chat_completion,
            _MEMORY_EXTRACT_PROMPT,
            conversation,
            256,
        )
        # 从响应中提取 JSON（可能有前后文字）
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return
        extracted = json.loads(raw[start:end])
        if not extracted:
            return

        from routes.memories import embed
        from database import get_db
        db = get_db()
        for item in extracted:
            content = item.get("content", "").strip()
            category = item.get("category", "fact").strip()
            if not content:
                continue
            try:
                embedding = await asyncio.to_thread(embed, content)
            except Exception:
                embedding = None
            insert_data: dict = {
                "user_id": user_id,
                "content": content,
                "category": category,
            }
            if embedding is not None:
                insert_data["embedding"] = embedding
            db.table("memories").insert(insert_data).execute()
    except Exception:
        pass


@router.post("/chat")
async def ui_chat(
    req: UIChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """网页端 AI 对话 — 自动注入记忆、保存历史"""
    from database import get_db
    db = get_db()

    memory_context = _fetch_memories(current_user["sub"], req.message)
    system_prompt = PIXEL_SYSTEM_PROMPT + memory_context

    reply_text = chat_completion(
        system_prompt=system_prompt,
        user_message=req.message,
        max_tokens=512,
    )

    # 保存对话历史
    try:
        db.table("conversations").insert([
            {"user_id": current_user["sub"], "role": "user", "content": req.message},
            {"user_id": current_user["sub"], "role": "pixel", "content": reply_text},
        ]).execute()
    except Exception:
        pass

    # 后台提取记忆（不阻塞响应）
    asyncio.create_task(
        _extract_and_save_memories(current_user["sub"], req.message, reply_text)
    )

    return {"reply": reply_text, "engine": get_engine_name()}


@router.post("/intent", response_model=IntentResponse)
async def ui_intent(
    req: IntentRequest,
    current_user: dict = Depends(get_current_user),
):
    """自然语言意图解析 — 将用户指令转为结构化动作"""
    raw = await asyncio.to_thread(
        chat_completion,
        _INTENT_PROMPT,
        req.text,
        256,
    )
    # 从响应中提取 JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return IntentResponse(
            action="chat",
            context="general",
            delay_minutes=0,
            output_type="none",
            translate_to="",
            reply="抱歉，我没能理解你的意图，请再说一次？",
        )
    parsed = json.loads(raw[start:end])
    return IntentResponse(**parsed)


@router.post("/speak")
async def ui_speak(
    req: UISpeakRequest,
    current_user: dict = Depends(get_current_user),
):
    """TTS 语音合成"""
    voice = VOICE_MAP.get(req.lang, VOICE_MAP["zh"])
    communicate = edge_tts.Communicate(req.text, voice)
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return StreamingResponse(
        audio_buffer,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=pixel.mp3"},
    )
