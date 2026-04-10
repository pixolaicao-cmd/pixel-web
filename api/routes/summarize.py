"""
POST /summarize — 笔记总结 / 文档模式
mode=summary (默认): 返回 {summary, key_points} JSON
mode=document:       返回 {markdown, summary, key_points} — 结构化 Markdown 文档
"""

import json
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import verify_token
from config import (
    SUMMARIZE_SYSTEM_PROMPT, DOCUMENT_SYSTEM_PROMPT,
    AI_ENGINE, GOOGLE_API_KEY, XAI_API_KEY, ANTHROPIC_API_KEY,
)
from ai_client import chat_completion

router = APIRouter()


def _extract_json(text: str) -> str:
    """从模型输出中提取 JSON，处理 <thought> 标签和代码块包装。"""
    # 去掉 <thought>...</thought> 思考块（含内部换行）
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL).strip()
    # 去掉 ```json ... ``` 或 ``` ... ``` 包装
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


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

    try:
        if req.mode == "document":
            # 文档模式：返回完整结构化 Markdown
            markdown = await chat_completion(
                system_prompt=DOCUMENT_SYSTEM_PROMPT,
                user_message=req.transcript,
                max_tokens=4096,
            )
            # 清理 <thought> 标签和 code fence
            clean_md = re.sub(r"<thought>.*?</thought>", "", markdown, flags=re.DOTALL).strip()
            if clean_md.startswith("```"):
                clean_md = clean_md.split("\n", 1)[1]
                clean_md = clean_md.rsplit("```", 1)[0].strip()

            # 同时提取一个简短摘要
            summary_text = await chat_completion(
                system_prompt=SUMMARIZE_SYSTEM_PROMPT,
                user_message=req.transcript,
                max_tokens=1024,
            )
            summary = ""
            key_points: list[str] = []
            try:
                s = _extract_json(summary_text)
                data = json.loads(s)
                summary = data.get("summary", "")
                key_points = data.get("key_points", [])
            except (json.JSONDecodeError, KeyError):
                summary = summary_text[:300]

            return SummarizeResponse(summary=summary, key_points=key_points, markdown=clean_md)

        # 默认摘要模式
        raw_text = await chat_completion(
            system_prompt=SUMMARIZE_SYSTEM_PROMPT,
            user_message=req.transcript,
            max_tokens=2048,
        )

        try:
            clean_text = _extract_json(raw_text)
            data = json.loads(clean_text)
            return SummarizeResponse(
                summary=data.get("summary", raw_text),
                key_points=data.get("key_points", []),
            )
        except (json.JSONDecodeError, KeyError):
            return SummarizeResponse(summary=raw_text, key_points=[])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error [{AI_ENGINE}]: {type(e).__name__}: {str(e)[:300]}")
