"""
速率限制 — 使用 slowapi（内存后端）

说明：
- Vercel Fluid Compute 会复用函数实例，内存限流器在单实例内有效
- 多实例之间不共享状态，但仍能有效挡住针对单实例的暴力破解
- 如需更强保护，可接入 Upstash Redis 或 Vercel BotID
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_key(request) -> str:
    """优先用 Vercel/Cloudflare 提供的真实客户端 IP，回退到 remote_address。"""
    headers = request.headers
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        # x-forwarded-for 可能是 "client, proxy1, proxy2" — 取第一个
        return forwarded.split(",")[0].strip()
    real_ip = headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_key, default_limits=[])
