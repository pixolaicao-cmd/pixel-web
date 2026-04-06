"""
用户注册 / 登录 / 个人信息
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from database import get_db
from user_auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/users")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(default="")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    name: str


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    db = get_db()

    # 检查邮箱是否已存在
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
    token = create_token(user["id"], user["email"])

    return AuthResponse(
        token=token,
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    db = get_db()

    result = db.table("users").select("*").eq("email", req.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["email"])

    return AuthResponse(
        token=token,
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    db = get_db()
    result = db.table("users").select("id, email, name, created_at").eq("id", current_user["sub"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data[0]
