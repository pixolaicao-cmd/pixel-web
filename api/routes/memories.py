"""
记忆系统 — 存储时生成向量 embedding，搜索时用余弦相似度
使用 sentence-transformers 本地模型（多语言，支持中文/挪威语/英语）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from database import get_db
from user_auth import get_current_user
import json

router = APIRouter(prefix="/memories")

# 懒加载模型，第一次调用时初始化
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model

def embed(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text).tolist()


class CreateMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(default="general")


@router.get("")
async def list_memories(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """获取用户的所有记忆。"""
    db = get_db()
    result = (
        db.table("memories")
        .select("id, content, category, created_at")
        .eq("user_id", current_user["sub"])
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"memories": result.data}


@router.post("")
async def create_memory(
    req: CreateMemoryRequest,
    current_user: dict = Depends(get_current_user),
):
    """创建一条记忆，自动生成向量 embedding。"""
    db = get_db()
    try:
        embedding = embed(req.content)
    except Exception:
        embedding = None
    insert_data: dict = {
        "user_id": current_user["sub"],
        "content": req.content,
        "category": req.category,
    }
    if embedding is not None:
        insert_data["embedding"] = embedding
    result = db.table("memories").insert(insert_data).execute()
    return result.data[0]


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: dict = Depends(get_current_user),
):
    """删除一条记忆。"""
    db = get_db()
    db.table("memories").delete().eq("id", memory_id).eq("user_id", current_user["sub"]).execute()
    return {"status": "deleted"}


@router.get("/search")
async def search_memories(
    q: str,
    limit: int = Query(default=5, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """向量语义搜索记忆。"""
    db = get_db()
    try:
        query_embedding = embed(q)
    except Exception:
        query_embedding = None

    # 用 Supabase RPC 做向量相似度搜索
    if query_embedding is not None:
        try:
            result = db.rpc("match_memories", {
                "query_embedding": query_embedding,
                "match_user_id": current_user["sub"],
                "match_count": limit,
            }).execute()
            return {"memories": result.data}
        except Exception:
            pass

    # 降级到文本搜索
    result = (
        db.table("memories")
        .select("id, content, category, created_at")
        .eq("user_id", current_user["sub"])
        .ilike("content", f"%{q}%")
        .limit(limit)
        .execute()
    )
    return {"memories": result.data}
