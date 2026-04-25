"""
用户注册 / 登录 / Google OAuth / 个人信息
"""

import urllib.parse
import httpx

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, EmailStr
from database import get_db
from user_auth import hash_password, verify_password, create_token, get_current_user
from rate_limit import limiter
from config import (
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_OAUTH_REDIRECT_URI,
)

router = APIRouter(prefix="/users")


# ── 请求 / 响应模型 ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(default="")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = True   # True → 7天；False → 72小时（关闭浏览器登出）


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    name: str
    remember_me: bool = True   # 前端据此决定 localStorage vs sessionStorage


# ── 邮箱注册 ────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
@limiter.limit("3/minute;20/hour")
async def register(request: Request, req: RegisterRequest):
    db = get_db()

    existing = db.table("users").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(req.password)
    result = db.table("users").insert({
        "email": req.email,
        "password_hash": hashed,
        "name": req.name or req.email.split("@")[0],
    }).execute()

    user = result.data[0]
    token = create_token(user["id"], user["email"], remember_me=True)

    return AuthResponse(
        token=token,
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
        remember_me=True,
    )


# ── 邮箱登录 ────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute;50/hour")
async def login(request: Request, req: LoginRequest):
    db = get_db()

    result = db.table("users").select("*").eq("email", req.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["email"], remember_me=req.remember_me)

    return AuthResponse(
        token=token,
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
        remember_me=req.remember_me,
    )


# ── Google OAuth ─────────────────────────────────────────────

def _google_configured() -> bool:
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)


@router.get("/google/authorize")
@limiter.limit("10/minute")
async def google_authorize(request: Request):
    """把用户重定向到 Google 授权页面。"""
    if not _google_configured():
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    params = urllib.parse.urlencode({
        "client_id":     GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri":  GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
        "prompt":        "select_account",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
async def google_callback(code: str = "", error: str = ""):
    """Google 回调：换 token → 取用户信息 → 创建/找到用户 → 签发 JWT → 跳回前端。"""
    if error or not code:
        return RedirectResponse("/login?error=google_denied")

    if not _google_configured():
        return RedirectResponse("/login?error=google_not_configured")

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. 换 access_token
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri":  GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type":    "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return RedirectResponse("/login?error=google_token_failed")
        access_token = token_resp.json().get("access_token", "")

        # 2. 取 Google 用户信息
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            return RedirectResponse("/login?error=google_userinfo_failed")
        guser = userinfo_resp.json()

    email = guser.get("email", "")
    name  = guser.get("name", "") or email.split("@")[0]

    if not email:
        return RedirectResponse("/login?error=google_no_email")

    db = get_db()

    # 3. 查找或创建用户
    existing = db.table("users").select("*").eq("email", email).execute()
    if existing.data:
        user = existing.data[0]
    else:
        result = db.table("users").insert({
            "email":         email,
            "password_hash": "",   # Google 用户无密码
            "name":          name,
        }).execute()
        user = result.data[0]

    # 4. 签发 7天 JWT（Google 登录默认记住）
    token = create_token(user["id"], user["email"], remember_me=True)

    # 5. 重定向到前端 /auth/callback，由 Next.js 页面写入 localStorage
    params = urllib.parse.urlencode({
        "token":   token,
        "user_id": user["id"],
        "email":   user["email"],
        "name":    user["name"],
    })
    return RedirectResponse(f"/auth/callback?{params}")


# ── 当前用户信息 ─────────────────────────────────────────────

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    db = get_db()
    result = db.table("users").select("id, email, name, created_at").eq("id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data[0]
