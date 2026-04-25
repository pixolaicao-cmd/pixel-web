"""
POST /transcribe — 语音转文字
使用 Gemini 2.5 Flash multimodal（中文识别准确，跟 voice 路由用同一引擎）。
仅支持短录音（≤ 20MB，约 9 分钟以内）。长会议/课堂下个版本上 File API。
"""

import os
import json
import base64
import httpx
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from auth import verify_token
from config import GOOGLE_API_KEY

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "audio/webm",
    "application/octet-stream",  # ESP32 可能发送此类型
}

# Gemini inline base64 实测限制 ~20MB（base64 膨胀后接近 API 总 payload 上限）
# 对应约 9 分钟 16kHz Opus 音频；更长的需要换 File API（下个版本）
MAX_FILE_SIZE = 20 * 1024 * 1024

GEMINI_MODEL = os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def _gemini_audio_mime(raw_mime: str) -> str:
    """Gemini 不认 audio/webm，但 webm 装的就是 Opus，和 ogg 同 codec。"""
    base = raw_mime.split(";")[0].strip().lower()
    if base == "audio/webm":
        return "audio/ogg"
    return base


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    _: None = Depends(verify_token),
):
    """接收音频文件，返回转写文字及检测到的语言。"""
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    raw_content_type = file.content_type or "application/octet-stream"
    content_type = raw_content_type.split(";")[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {raw_content_type}",
        )

    audio_data = await file.read()
    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(audio_data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(audio_data) / 1024 / 1024:.1f}MB. "
                   f"当前版本仅支持 ≤ 20MB（约 9 分钟）短录音。"
                   f"长会议/课堂转写正在开发中。",
        )

    audio_b64 = base64.b64encode(audio_data).decode("ascii")
    audio_mime = _gemini_audio_mime(raw_content_type)

    # 只做转写，不让 LLM 加自己的话
    instructions = (
        '请把这段音频精确转写成文字。要求：\n'
        '1. 保留原始语言（中文/英文/挪威语等）\n'
        '2. 不要总结，不要润色，逐字转写（口语化的「嗯」「那个」等可以保留）\n'
        '3. 多个说话人时用换行分隔\n'
        '4. 只输出 JSON：{"transcript": "<转写文字>", "language": "<zh/en/no/...>"}\n'
        '不要 markdown 代码块，不要任何解释。'
    )

    body = {
        "contents": [{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": audio_mime, "data": audio_b64}},
                {"text": instructions},
            ],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192,  # 长录音转写文字多，给充足 token
            "temperature": 0.0,        # 转写要确定性
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                GEMINI_URL,
                params={"key": GOOGLE_API_KEY},
                json=body,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Gemini transcription timed out (录音可能过长，超过 2 分钟未返回)",
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini HTTP {resp.status_code}: {resp.text[:300]}",
        )

    data = resp.json()
    try:
        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(
            status_code=502,
            detail=f"Gemini unexpected response: {json.dumps(data)[:300]}",
        )

    finish_reason = candidate.get("finishReason", "")
    try:
        parsed = json.loads(text)
        transcript = (parsed.get("transcript") or "").strip()
        language = (parsed.get("language") or "").strip().lower()
    except json.JSONDecodeError:
        # 降级：JSON 失败时直接把原文当转写返回，至少不让用户白等
        transcript = text.strip()
        language = ""

    if not transcript:
        hint = ""
        if finish_reason == "MAX_TOKENS":
            hint = " (输出超长被截断 — 录音太长)"
        elif finish_reason == "SAFETY":
            hint = " (内容被安全过滤拦截)"
        raise HTTPException(
            status_code=422,
            detail=f"No speech detected{hint}",
        )

    return {"text": transcript, "language": language}
