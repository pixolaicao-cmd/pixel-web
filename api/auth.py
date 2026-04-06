"""
Pixel AI 挂件 — 简单 Token 验证
ESP32 请求时在 Header 中携带 Authorization: Bearer <token>
"""

from fastapi import Header, HTTPException
from config import API_TOKEN


async def verify_token(authorization: str = Header(default="")):
    """验证请求 Token。如果未配置 API_TOKEN 则跳过验证（开发模式）。"""
    if not API_TOKEN:
        return

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.removeprefix("Bearer ")
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
