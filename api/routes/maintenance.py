"""
内部维护接口 — Vercel Cron 调用
鉴权：CRON_SECRET 环境变量（Vercel Cron 自动带 Authorization: Bearer $CRON_SECRET）
"""

import os
from fastapi import APIRouter, Header, HTTPException

from database import get_db

router = APIRouter(prefix="/cron")


def _verify_cron_secret(authorization: str | None) -> None:
    secret = os.getenv("CRON_SECRET")
    if not secret:
        # 没设置 CRON_SECRET → 拒绝调用，避免无认证的破坏性接口
        raise HTTPException(status_code=503, detail="CRON_SECRET not configured")
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/cleanup-conversations")
async def cleanup_expired_conversations(
    authorization: str | None = Header(default=None),
):
    """删除 expires_at 已过期的对话行（Pixel 短期上下文）。
    永久档案（expires_at IS NULL）不动。
    """
    _verify_cron_secret(authorization)
    db = get_db()
    # PostgREST 的 .lt() 把现在传给 expires_at < now() 的过滤
    # 这里直接用 SQL 走 RPC 不太干净，用 supabase-py 的 lte/now 替代方案：
    # 让 Postgres 自己计算 now()
    result = (
        db.table("conversations")
        .delete()
        .lt("expires_at", "now()")
        .execute()
    )
    deleted = len(result.data) if result.data else 0
    print(f"[cron] cleanup-conversations deleted {deleted} expired rows")
    return {"deleted": deleted}
