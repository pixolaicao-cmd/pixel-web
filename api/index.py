"""
Pixel AI — Vercel Python 入口
所有路由统一挂在 /api/* 下，和 Next.js 前端同域部署。
"""

import sys
import os

# 确保 api/ 目录在 Python path 里，routes/ 可以被正常导入
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import transcribe, chat, speak, summarize, translate, users, conversations, notes, memories, soul, ui, voice, devices

app = FastAPI(
    title="Pixel AI Backend",
    description="Pixel 挂脖式 AI 智能伙伴",
    version="1.0.0",
)

# 开发环境允许 localhost，生产环境同域不需要 CORS 但保留兼容
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 所有路由统一加 /api 前缀
PREFIX = "/api"

app.include_router(transcribe.router, prefix=PREFIX, tags=["STT"])
app.include_router(chat.router,       prefix=PREFIX, tags=["Chat"])
app.include_router(speak.router,      prefix=PREFIX, tags=["TTS"])
app.include_router(summarize.router,  prefix=PREFIX, tags=["Summarize"])
app.include_router(translate.router,  prefix=PREFIX, tags=["Translate"])
app.include_router(users.router,      prefix=PREFIX, tags=["Users"])
app.include_router(conversations.router, prefix=PREFIX, tags=["Conversations"])
app.include_router(notes.router,      prefix=PREFIX, tags=["Notes"])
app.include_router(memories.router,   prefix=PREFIX, tags=["Memories"])
app.include_router(soul.router,       prefix=PREFIX, tags=["Soul"])
app.include_router(ui.router,         prefix=PREFIX, tags=["UI"])
app.include_router(voice.router,      prefix=PREFIX, tags=["Voice"])
app.include_router(devices.router,    prefix=PREFIX, tags=["Devices"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    from config import AI_ENGINE, GROK_MODEL, CLAUDE_MODEL, OLLAMA_MODEL
    from ai_client import get_engine_name
    return {
        "status": "ok",
        "engine": AI_ENGINE,
        "engine_name": get_engine_name(),
        "models": {"grok": GROK_MODEL, "claude": CLAUDE_MODEL, "ollama": OLLAMA_MODEL},
    }
