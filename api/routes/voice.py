"""
POST /voice — 设备主循环接口
音频文件进 → STT → AI 对话 → TTS → 音频流出

一次 HTTP 请求完成完整对话循环，专为 ESP32-S3 低延迟设计。
响应头携带文字信息，方便调试。
"""

import os
import io
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from deepgram import DeepgramClient, PrerecordedOptions
import edge_tts

from auth import verify_token
from user_auth import get_current_user_optional
from config import PIXEL_SYSTEM_PROMPT, DEEPGRAM_API_KEY
from ai_client import chat_completion

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
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=500, detail="DEEPGRAM_API_KEY not configured")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_AUDIO:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {content_type}")

    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")

    # ── 1. STT (Deepgram) ─────────────────────────────────
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        options = PrerecordedOptions(
            model="nova-3",
            detect_language=True,
            smart_format=True,
        )
        resp = deepgram.listen.rest.v("1").transcribe_file(
            {"buffer": audio_data, "mimetype": content_type},
            options,
        )
        channel = resp.results.channels[0]
        transcript = channel.alternatives[0].transcript.strip()
        detected_lang = getattr(channel, "detected_language", "zh") or "zh"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"STT error: {e}")

    if not transcript:
        raise HTTPException(status_code=422, detail="No speech detected")

    # ── 2. AI 对话 ────────────────────────────────────────
    memory_context = ""
    if current_user:
        memory_context = _fetch_memories(current_user["sub"], transcript)

    system_prompt = PIXEL_SYSTEM_PROMPT + memory_context

    try:
        reply_text = await chat_completion(
            system_prompt=system_prompt,
            user_message=transcript,
            max_tokens=256,  # 语音回复要简短
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    # ── 3. TTS (edge-tts) ────────────────────────────────
    # 语言映射：优先用检测到的语言
    lang_code = "zh"
    if detected_lang:
        dl = detected_lang.lower()
        if dl.startswith("zh"):
            lang_code = "zh"
        elif dl.startswith("nb") or dl.startswith("no"):
            lang_code = "no"
        elif dl.startswith("en"):
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

    # ── 4. 后台保存对话（不阻塞响应）────────────────────
    if current_user:
        import asyncio
        async def _save():
            try:
                from database import get_db
                get_db().table("conversations").insert([
                    {"user_id": current_user["sub"], "role": "user",  "content": transcript},
                    {"user_id": current_user["sub"], "role": "pixel", "content": reply_text},
                ]).execute()
            except Exception:
                pass
        asyncio.create_task(_save())

    # 文字编码成 ASCII-safe header（去掉非 Latin-1 字符用 URL encoding）
    from urllib.parse import quote
    return StreamingResponse(
        audio_buffer,
        media_type="audio/mpeg",
        headers={
            "X-Transcript": quote(transcript[:200]),
            "X-Reply":      quote(reply_text[:200]),
            "X-Language":   detected_lang or "zh",
            "Content-Disposition": "inline; filename=pixel_reply.mp3",
        },
    )
