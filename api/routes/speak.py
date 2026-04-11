"""
POST /speak — 文字转语音

方案优先级：
1. edge-tts Python 库（免费，直接调用微软 Edge TTS 服务）
2. OpenAI TTS API（付费备选）
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import edge_tts
import io
from auth import verify_token

OPENAI_API_KEY = ""  # 备用，目前未启用

router = APIRouter()

# 声音配置 — 微软 Neural 声音
VOICE_MAP = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "no": "nb-NO-PernilleNeural",
    "en": "en-US-JennyNeural",
}
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    lang: str = Field(default="zh", pattern="^(zh|no|en)$")


async def _tts_via_edge(text: str, voice: str) -> io.BytesIO:
    """通过 edge-tts 库直接生成语音（免费）。"""
    communicate = edge_tts.Communicate(text, voice)
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return audio_buffer


async def _tts_via_openai(text: str) -> io.BytesIO:
    """通过 OpenAI TTS API 生成语音（付费备选）。"""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="mp3",
    )
    return io.BytesIO(response.content)


@router.post("/speak")
async def speak(
    req: SpeakRequest,
    _: None = Depends(verify_token),
):
    """接收文字，返回 MP3 音频流。"""
    voice = VOICE_MAP.get(req.lang, DEFAULT_VOICE)

    # 方案 1：edge-tts（免费）
    try:
        audio_buffer = await _tts_via_edge(req.text, voice)
        if audio_buffer.getbuffer().nbytes > 0:
            return StreamingResponse(
                audio_buffer,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=pixel_speech.mp3"},
            )
    except Exception:
        pass

    # 方案 2：OpenAI TTS（付费备选）
    if OPENAI_API_KEY:
        try:
            audio_buffer = await _tts_via_openai(req.text)
            if audio_buffer.getbuffer().nbytes > 0:
                return StreamingResponse(
                    audio_buffer,
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": "inline; filename=pixel_speech.mp3"},
                )
        except Exception:
            pass

    raise HTTPException(status_code=503, detail="TTS 服务不可用")
