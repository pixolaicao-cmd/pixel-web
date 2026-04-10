"""
POST /translate — 实时翻译
检测源语言，自动翻译到目标语言：
  中文 → 挪威语
  挪威语/英语 → 中文
返回翻译文字 + 检测到的源语言 + 目标语言
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from auth import verify_token
from ai_client import chat_completion

router = APIRouter()

LANG_MAP = {
    "zh": "no",   # 中文 → 挪威语
    "no": "zh",   # 挪威语 → 中文
    "en": "zh",   # 英语 → 中文（默认）
}

LANG_NAME = {
    "zh": "中文",
    "no": "norsk",
    "en": "English",
}

TRANSLATE_PROMPT = """你是一个专业翻译。请将用户发送的文字翻译成 {target_lang_name}。
规则：
- 只输出翻译结果，不要解释，不要加任何前缀
- 保持原文的语气和风格
- 如果是口语，翻译成自然的口语
- 翻译要简洁准确"""


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(default="auto")   # "zh"/"no"/"en"/"auto"
    target_lang: str = Field(default="auto")   # "auto" = 自动根据源语言决定


class TranslateResponse(BaseModel):
    translation: str
    source_lang: str
    target_lang: str


@router.post("/translate", response_model=TranslateResponse, tags=["Translate"])
async def translate(
    req: TranslateRequest,
    _: None = Depends(verify_token),
):
    """自动检测语言并翻译。"""
    src = req.source_lang if req.source_lang != "auto" else "zh"
    tgt = req.target_lang if req.target_lang != "auto" else LANG_MAP.get(src, "en")

    tgt_name = LANG_NAME.get(tgt, tgt)
    prompt = TRANSLATE_PROMPT.format(target_lang_name=tgt_name)

    translation = await chat_completion(
        system_prompt=prompt,
        user_message=req.text,
        max_tokens=512,
    )

    return TranslateResponse(
        translation=translation,
        source_lang=src,
        target_lang=tgt,
    )
