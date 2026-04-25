"""
POST /transcribe — 语音转文字
使用 Deepgram Nova-3，支持自动语言检测（中文、日语、韩语、挪威语、瑞典语、丹麦语、芬兰语、英语等）。
"""

import os
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from deepgram import DeepgramClient, PrerecordedOptions
from auth import verify_token

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "audio/webm",
    "application/octet-stream",  # ESP32 可能发送此类型
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    _: None = Depends(verify_token),
):
    """接收音频文件，返回转写文字及检测到的语言。"""
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    if not deepgram_api_key:
        raise HTTPException(status_code=500, detail="DEEPGRAM_API_KEY not configured")

    raw_content_type = file.content_type or "application/octet-stream"
    content_type = raw_content_type.split(";")[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {raw_content_type}",
        )

    audio_data = await file.read()
    if len(audio_data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    deepgram = DeepgramClient(deepgram_api_key)
    options = PrerecordedOptions(
        model="nova-3",
        detect_language=True,
        smart_format=True,
    )

    response = deepgram.listen.rest.v("1").transcribe_file(
        {"buffer": audio_data, "mimetype": content_type},
        options,
    )

    channel = response.results.channels[0]
    transcript = channel.alternatives[0].transcript
    detected_lang = getattr(channel, "detected_language", None)

    return {"text": transcript.strip(), "language": detected_lang}
