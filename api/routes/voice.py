"""
POST /voice — 设备主循环接口
音频文件进 → Gemini 2.5 Flash（STT + 回复合并）→ TTS → 音频流出

一次 HTTP 请求完成完整对话循环，专为 ESP32-S3 低延迟设计。
响应头携带文字信息，方便调试。
"""

import os
import io
import json
import base64
import httpx
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import edge_tts

from auth import verify_token
from user_auth import get_current_user_optional
from config import PIXEL_SYSTEM_PROMPT, GOOGLE_API_KEY

router = APIRouter()

ALLOWED_AUDIO = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "audio/webm",
    "application/octet-stream",
}

VOICE_MAP = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "no": "nb-NO-PernilleNeural",
    "en": "en-US-JennyNeural",
}

GEMINI_MODEL = os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Gemini 官方支持：wav / mp3 / aiff / aac / ogg / flac
# WebM 容器装的是 Opus，和 OGG 一样的 codec — 把 mime 改成 audio/ogg 让 Gemini 接收
def _gemini_audio_mime(raw_mime: str) -> str:
    base = raw_mime.split(";")[0].strip().lower()
    if base in ("audio/webm",):
        return "audio/ogg"
    return base


async def _gemini_voice_call(
    audio_bytes: bytes,
    audio_mime: str,
    system_prompt: str,
) -> dict:
    """一次调用：音频 → {transcript, language, reply}"""
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    instructions = (
        "用户刚刚发送了一段语音。请你完成两件事，并以 JSON 格式输出：\n"
        '{\n'
        '  "transcript": "<用户原话的精确转写，保留原始语言>",\n'
        '  "language":   "<zh / en / no 三选一，根据用户实际说的语言>",\n'
        '  "reply":      "<你的口语化回复，使用和用户相同的语言，不超过3句话>"\n'
        '}\n'
        "只输出 JSON，不要任何其他内容、不要 markdown 代码块、不要思考过程。"
    )
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": audio_mime, "data": audio_b64}},
                {"text": instructions},
            ],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 1024,
            "temperature": 0.7,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GEMINI_URL,
            params={"key": GOOGLE_API_KEY},
            json=body,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini unexpected response: {json.dumps(data)[:300]}")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Gemini non-JSON output: {text[:300]}")
    return parsed


def _fetch_memories(user_id: str, query: str, limit: int = 5) -> str:
    try:
        from routes.memories import embed
        from database import get_db
        embedding = embed(query)
        result = get_db().rpc("match_memories", {
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


def _fetch_recent_conversation(user_id: str, limit: int = 30) -> str:
    """拉最近 N 条对话作为记忆上下文，让 AI 跨天保持连贯。"""
    try:
        from database import get_db
        from datetime import datetime, timezone
        result = (
            get_db().table("conversations")
            .select("role,content,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(result.data or []))
        if not rows:
            return ""
        now = datetime.now(timezone.utc)
        lines = []
        for r in rows:
            speaker = "用户" if r["role"] == "user" else "你（Pixel）"
            content = (r.get("content") or "").strip()
            if not content:
                continue
            ts_label = ""
            try:
                ts_str = r.get("created_at") or ""
                # Supabase 返回 ISO 格式，可能带 Z 或 +00:00
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta = now - ts
                if delta.total_seconds() < 60:
                    ts_label = "[刚刚] "
                elif delta.total_seconds() < 3600:
                    ts_label = f"[{int(delta.total_seconds() // 60)}分钟前] "
                elif delta.total_seconds() < 86400:
                    ts_label = f"[{int(delta.total_seconds() // 3600)}小时前] "
                else:
                    days = int(delta.total_seconds() // 86400)
                    ts_label = f"[{days}天前] "
            except Exception:
                pass
            lines.append(f"{ts_label}{speaker}：{content}")
        if not lines:
            return ""
        return (
            "\n\n【你和这个用户的对话历史 — 这就是你的记忆，必须使用】\n"
            + "\n".join(lines)
            + "\n【历史结束】\n"
            "如果用户问起之前聊过什么，从上面引用具体内容回答；不要说"
            "\"我没有记忆\" — 你明明记得。"
        )
    except Exception:
        return ""


@router.post("/voice")
async def voice_pipeline(
    file: UploadFile = File(...),
    _: None = Depends(verify_token),
    current_user: dict | None = Depends(get_current_user_optional),
):
    """
    完整语音对话管道：音频 → STT → AI → TTS → 音频

    响应 Header：
      X-Transcript: 转写原文
      X-Reply:      AI 回复文字
      X-Language:   检测到的语言
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    raw_content_type = file.content_type or "application/octet-stream"
    content_type = raw_content_type.split(";")[0].strip().lower()
    if content_type not in ALLOWED_AUDIO:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {raw_content_type}")

    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")

    # ── 1+2. Gemini 2.5 Flash 一站式：STT + 对话回复 ─────────
    # 之前两步（Deepgram → Gemma 31B）总耗时 24s 且中文识别错误。
    # 合并成一次 Gemini multimodal 调用：音频直接进 LLM，省一次往返。
    history_context = ""
    if current_user:
        # 记忆上下文：最近 30 条对话（覆盖最近几天），让 AI 跨天保持连贯
        history_context = _fetch_recent_conversation(current_user["sub"], limit=30)
    system_prompt = PIXEL_SYSTEM_PROMPT + history_context

    try:
        result = await _gemini_voice_call(
            audio_bytes=audio_data,
            audio_mime=_gemini_audio_mime(raw_content_type),
            system_prompt=system_prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    transcript = (result.get("transcript") or "").strip()
    reply_text = (result.get("reply") or "").strip()
    detected_lang = (result.get("language") or "zh").strip().lower()

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail=f"No speech detected (mimetype={raw_content_type}, bytes={len(audio_data)})",
        )
    if not reply_text:
        raise HTTPException(status_code=502, detail="AI returned empty reply")

    # ── 3. TTS (edge-tts) ────────────────────────────────
    lang_code = "zh"
    if detected_lang.startswith("zh"):
        lang_code = "zh"
    elif detected_lang.startswith("nb") or detected_lang.startswith("no"):
        lang_code = "no"
    elif detected_lang.startswith("en"):
        lang_code = "en"

    voice = VOICE_MAP.get(lang_code, VOICE_MAP["zh"])
    try:
        communicate = edge_tts.Communicate(reply_text, voice)
        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
        audio_buffer.seek(0)
        if audio_buffer.getbuffer().nbytes == 0:
            raise ValueError("Empty TTS output")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS error: {e}")

    # ── 4. 同步保存对话 ──────────────────────────────────
    # 不能用 asyncio.create_task —— Vercel serverless 在 response 发出后
    # 立刻冻结函数实例，后台 task 会被丢弃。必须 await 完成再返回。
    saved_ok = False
    if current_user:
        try:
            from database import get_db
            get_db().table("conversations").insert([
                {"user_id": current_user["sub"], "role": "user",  "content": transcript},
                {"user_id": current_user["sub"], "role": "pixel", "content": reply_text},
            ]).execute()
            saved_ok = True
        except Exception as e:
            # 不阻塞用户体验，但要让前端知道
            print(f"[voice] save conversation failed: {e}")

    # 文字编码成 ASCII-safe header（去掉非 Latin-1 字符用 URL encoding）
    from urllib.parse import quote
    return StreamingResponse(
        audio_buffer,
        media_type="audio/mpeg",
        headers={
            "X-Transcript":   quote(transcript[:200]),
            "X-Reply":        quote(reply_text[:200]),
            "X-Language":     detected_lang or "zh",
            "X-Saved":        "1" if saved_ok else "0",
            "X-History-Used": str(len(history_context)),
            "Content-Disposition": "inline; filename=pixel_reply.mp3",
        },
    )
