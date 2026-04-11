"""
设备绑定 API — Pixel AI 挂件
流程：
  1. ESP32 开机 → POST /api/devices/register  → 获得 6 位配对码
  2. 用户在 App 输入配对码 → POST /api/devices/pair  → 设备绑定到账号
  3. ESP32 轮询 → GET  /api/devices/status/{device_id} → 等待配对完成
  4. 配对后 ESP32 得到永久 device_token，存入 NVS Flash
"""

import os
import secrets
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from database import get_db
from user_auth import get_current_user
from auth import verify_token

router = APIRouter()

PAIRING_TTL_MINUTES = 10  # 配对码有效期


# ── 数据模型 ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    device_id: str = Field(..., min_length=6, max_length=64,
                            description="设备唯一 ID，如 MAC 地址")
    firmware_version: str = Field(default="0.1.0", max_length=20)
    model: str = Field(default="CoreS3", max_length=40)


class PairRequest(BaseModel):
    pairing_code: str = Field(..., min_length=6, max_length=6)


# ── 辅助函数 ──────────────────────────────────────────────

def _gen_pairing_code() -> str:
    """生成 6 位数字配对码。"""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _gen_device_token() -> str:
    """生成 64 字符设备永久 Token。"""
    return secrets.token_hex(32)


# ── 路由 ─────────────────────────────────────────────────

@router.post("/devices/register")
async def register_device(req: RegisterRequest, _: None = Depends(verify_token)):
    """
    设备注册/续期。
    - 新设备：创建记录，返回配对码
    - 已配对设备：返回 already_paired 状态
    - 配对中：刷新配对码
    """
    db = get_db()
    now = datetime.now(timezone.utc)

    result = db.table("devices").select("*").eq("device_id", req.device_id).execute()
    existing = result.data[0] if result.data else None

    if existing and existing.get("user_id"):
        # 已绑定账号，直接返回（不再发配对码）
        return {
            "status": "already_paired",
            "device_id": req.device_id,
            "message": "Device already linked to an account.",
        }

    pairing_code = _gen_pairing_code()
    expires_at = (now + timedelta(minutes=PAIRING_TTL_MINUTES)).isoformat()

    if existing:
        # 刷新配对码
        db.table("devices").update({
            "pairing_code": pairing_code,
            "pairing_expires_at": expires_at,
            "firmware_version": req.firmware_version,
            "model": req.model,
            "last_seen_at": now.isoformat(),
        }).eq("device_id", req.device_id).execute()
    else:
        # 新设备
        db.table("devices").insert({
            "device_id": req.device_id,
            "pairing_code": pairing_code,
            "pairing_expires_at": expires_at,
            "firmware_version": req.firmware_version,
            "model": req.model,
            "last_seen_at": now.isoformat(),
        }).execute()

    return {
        "status": "awaiting_pair",
        "pairing_code": pairing_code,
        "expires_in_seconds": PAIRING_TTL_MINUTES * 60,
        "message": f"Enter code {pairing_code} in the Pixel app.",
    }


@router.post("/devices/pair")
async def pair_device(req: PairRequest, current_user: dict = Depends(get_current_user)):
    """
    用户在 App 输入 6 位配对码，将设备绑定到当前账号。
    成功后生成永久 device_token。
    """
    db = get_db()
    now = datetime.now(timezone.utc)

    result = db.table("devices").select("*").eq("pairing_code", req.pairing_code).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Invalid pairing code")

    device = result.data[0]

    # 检查是否过期
    expires_at_str = device.get("pairing_expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if now > expires_at:
                raise HTTPException(status_code=410, detail="Pairing code expired. Please restart device.")
        except ValueError:
            pass

    # 检查是否已被其他账号绑定
    if device.get("user_id") and device["user_id"] != current_user["sub"]:
        raise HTTPException(status_code=409, detail="Device already linked to another account")

    device_token = _gen_device_token()

    db.table("devices").update({
        "user_id": current_user["sub"],
        "device_token": device_token,
        "pairing_code": None,
        "pairing_expires_at": None,
        "paired_at": now.isoformat(),
    }).eq("device_id", device["device_id"]).execute()

    return {
        "status": "paired",
        "device_id": device["device_id"],
        "model": device.get("model", "CoreS3"),
        "message": "Device successfully linked to your account!",
    }


@router.get("/devices/status/{device_id}")
async def device_status(device_id: str, _: None = Depends(verify_token)):
    """
    ESP32 轮询此接口，等待用户完成配对。
    配对完成后返回 device_token 供设备存入 Flash。
    """
    db = get_db()

    result = db.table("devices").select(
        "device_id, user_id, device_token, paired_at, model, firmware_version"
    ).eq("device_id", device_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Device not found. Call /register first.")

    device = result.data[0]

    # 更新最后在线时间
    db.table("devices").update({
        "last_seen_at": datetime.now(timezone.utc).isoformat()
    }).eq("device_id", device_id).execute()

    if device.get("user_id") and device.get("device_token"):
        return {
            "status": "paired",
            "device_token": device["device_token"],
            "paired_at": device.get("paired_at"),
        }

    return {"status": "awaiting_pair"}


@router.get("/devices")
async def list_my_devices(current_user: dict = Depends(get_current_user)):
    """列出当前用户绑定的所有设备（App 管理页面用）。"""
    db = get_db()
    result = db.table("devices").select(
        "device_id, model, firmware_version, paired_at, last_seen_at"
    ).eq("user_id", current_user["sub"]).order("paired_at", desc=True).execute()

    return {"devices": result.data or []}


@router.delete("/devices/{device_id}")
async def unlink_device(device_id: str, current_user: dict = Depends(get_current_user)):
    """解绑设备（不删记录，清除 user_id 和 token）。"""
    db = get_db()
    result = db.table("devices").select("user_id").eq("device_id", device_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Device not found")
    if result.data[0].get("user_id") != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not your device")

    db.table("devices").update({
        "user_id": None,
        "device_token": None,
        "paired_at": None,
    }).eq("device_id", device_id).execute()

    return {"status": "unlinked", "device_id": device_id}
