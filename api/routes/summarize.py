"""
POST /summarize — 笔记总结 / 文档模式
mode=summary (默认): 返回 {summary, key_points} JSON
mode=document:       返回 {markdown, summary, key_points}
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

# 摘要失败时的重试 prompt（更简短、更强硬）
_RETRY_SYSTEM_PROMPT = """输出纯 JSON，不要任何其他内容：
{"summary":"一句话总结","key_points":["要点1","要点2"]}"""


def _extract_json(text: str) -> str:
    """从模型输出中提取 JSON，处理 <thought> 标签和代码块包装（json_mode 失效时的兜底）。"""
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


async def _get_summary(transcript: str) -> tuple[str, list[str]]:
    """
    获取摘要 + 要点，带一次重试：
    - 第 1 次：json_mode=True（API 强制 JSON）
    - 第 2 次：更简单的 prompt + json_mode=True
    失败则返回原文截断 + 空列表
    """
    for attempt in range(2):
        system = SUMMARIZE_SYSTEM_PROMPT if attempt == 0 else _RETRY_SYSTEM_PROMPT
        raw = await chat_completion(
            system_prompt=system,
            user_message=transcript,
            max_tokens=2048,
            json_mode=True,
        )
        try:
            data = json.loads(_extract_json(raw))
            summary    = str(data.get("summary", "")).strip()
            key_points = [str(k) for k in data.get("key_points", []) if k]
            if summary:
                return summary, key_points
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # 重试

    # 两次都失败：降级返回原文
    return transcript[:300], []


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
    if AI_ENGINE == "gemma" and not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
    if AI_ENGINE == "grok" and not XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY not configured")
    if AI_ENGINE == "claude" and not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        if req.mode == "document":
            # 文档 + 摘要并行
            import asyncio
            doc_task     = chat_completion(DOCUMENT_SYSTEM_PROMPT, req.transcript, max_tokens=4096)
            summary_task = _get_summary(req.transcript)
            markdown_raw, (summary, key_points) = await asyncio.gather(doc_task, summary_task)

            # 清理文档输出
            clean_md = re.sub(r"<thought>.*?</thought>", "", markdown_raw, flags=re.DOTALL).strip()
            if clean_md.startswith("```"):
                clean_md = clean_md.split("\n", 1)[1]
                clean_md = clean_md.rsplit("```", 1)[0].strip()

            return SummarizeResponse(summary=summary, key_points=key_points, markdown=clean_md)

        # 默认摘要模式
        summary, key_points = await _get_summary(req.transcript)
        return SummarizeResponse(summary=summary, key_points=key_points)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI error [{AI_ENGINE}]: {type(e).__name__}: {str(e)[:300]}",
        )
