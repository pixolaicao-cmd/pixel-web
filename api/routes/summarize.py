"""
POST /summarize — 笔记总结
支持 Grok / Claude 双引擎，将长录音转写文字整理成结构化笔记。
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import verify_token
from config import SUMMARIZE_SYSTEM_PROMPT, XAI_API_KEY, ANTHROPIC_API_KEY, AI_ENGINE
from ai_client import chat_completion

router = APIRouter()


class SummarizeRequest(BaseModel):
    transcript: str = Field(..., min_length=10, max_length=50000)


class SummarizeResponse(BaseModel):
    summary: str
    key_points: list[str]


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    req: SummarizeRequest,
    _: None = Depends(verify_token),
):
    """接收长文字，返回结构化笔记摘要。"""
    if AI_ENGINE == "grok" and not XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY not configured")
    if AI_ENGINE == "claude" and not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    raw_text = chat_completion(
        system_prompt=SUMMARIZE_SYSTEM_PROMPT,
        user_message=req.transcript,
        max_tokens=2048,
    )

    # 尝试解析 JSON 格式的回复
    try:
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[1]
            clean_text = clean_text.rsplit("```", 1)[0]

        data = json.loads(clean_text)
        return SummarizeResponse(
            summary=data.get("summary", raw_text),
            key_points=data.get("key_points", []),
        )
    except (json.JSONDecodeError, KeyError):
        return SummarizeResponse(summary=raw_text, key_points=[])
