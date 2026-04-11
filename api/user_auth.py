"""
Pixel AI 挂件 — 用户认证（邮箱+密码 + JWT）
"""

from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException
import jwt
import bcrypt as _bcrypt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS, JWT_EXPIRE_HOURS_LONG


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, email: str, remember_me: bool = False) -> str:
    """
    remember_me=True  → 7天有效期（168小时）
    remember_me=False → 默认 72小时
    """
    hours = JWT_EXPIRE_HOURS_LONG if remember_me else JWT_EXPIRE_HOURS
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=hours),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """从 Authorization header 解析当前用户。"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ")
    return decode_token(token)


async def get_current_user_optional(authorization: str = Header(default="")) -> dict | None:
    """可选认证，未登录时返回 None 而不是报错。"""
    if not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.removeprefix("Bearer ")
        return decode_token(token)
    except Exception:
        return None
