"""
Pixel AI 挂件 — Supabase 数据库连接
"""

from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_client = None


def get_db():
    """获取 Supabase 客户端（单例）。"""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client
