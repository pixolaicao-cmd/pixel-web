"""
POST /summarize — 笔记总结 / 文档模式
mode=summary (默认): 返回 {summary, key_points} JSON
mode=document:       返回 {markdown, summary, key_points} — 结构化 Markdown 文档
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import verify_token
from config import (
    SUMMARIZE_SYSTEM_PROMPT, DOCUMENT_SYSTEM_PROMPT,
    AI_ENGINE, GOOGLE_API_KEY, XAI_API_KEY, ANTHROPIC_API_KEY,
)
from ai_client import chat_completion

router = APIRouter()


class SummarizeRequest(BaseModel):
    transcript: str = Field(..., min_length=10, max_length=50000)
    mode: str = Field(default="summary", pattern="^(summary|document)$")


class SummarizeResponse(BaseModel):
    summary: str
    key_points: list[str]
    markdown: str | None = None


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    req: SummarizeRequest,
    _: None = Depends(verify_token),
):
    """接收长文字，返回结构化笔记摘要或完整 Markdown 文档。"""
    if AI_ENGINE == "gemma" and not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
    if AI_ENGINE == "grok" and not XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY not configured")
    if AI_ENGINE == "claude" and not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    if req.mode == "document":
        # 文档模式：返回完整结构化 Markdown
        markdown = chat_completion(
            system_prompt=DOCUMENT_SYSTEM_PROMPT,
            user_message=req.transcript,
            max_tokens=4096,
        )
        # 清理可能的 code fence
        clean_md = markdown.strip()
        if clean_md.startswith("```"):
            clean_md = clean_md.split("\n", 1)[1]
            clean_md = clean_md.rsplit("```", 1)[0].strip()

        # 同时提取一个简短摘要
        summary_text = chat_completion(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            user_message=req.transcript,
            max_tokens=1024,
        )
        summary = ""
        key_points: list[str] = []
        try:
            s = summary_text.strip()
            if s.startswith("```"):
                s = s.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(s)
            summary = data.get("summary", "")
            key_points = data.get("key_points", [])
        except (json.JSONDecodeError, KeyError):
            summary = summary_text[:300]

        return SummarizeResponse(summary=summary, key_points=key_points, markdown=clean_md)

    # 默认摘要模式
    raw_text = chat_completion(
        system_prompt=SUMMARIZE_SYSTEM_PROMPT,
        user_message=req.transcript,
        max_tokens=2048,
    )

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
