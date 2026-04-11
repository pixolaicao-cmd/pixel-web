"""
Pixel AI 挂件 — 配置管理
引擎优先级：gemma（Google AI Studio Gemma 4）> ollama > grok > claude
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys — strip() 去除意外的换行和空格
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
XAI_API_KEY       = os.getenv("XAI_API_KEY", "").strip()
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY", "").strip()   # Google AI Studio

# AI 引擎: "gemma" | "ollama" | "grok" | "claude"
# 自动检测：有 GOOGLE_API_KEY → gemma，有 OLLAMA_BASE_URL → ollama，有 XAI_API_KEY → grok
AI_ENGINE = os.getenv("AI_ENGINE", "").lower()
if not AI_ENGINE:
    if GOOGLE_API_KEY:
        AI_ENGINE = "gemma"
    elif os.getenv("OLLAMA_BASE_URL"):
        AI_ENGINE = "ollama"
    elif XAI_API_KEY:
        AI_ENGINE = "grok"
    elif ANTHROPIC_API_KEY:
        AI_ENGINE = "claude"
    else:
        AI_ENGINE = "grok"

# Google AI Studio — Gemma 4（OpenAI 兼容格式）
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMMA_MODEL     = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")

# Ollama — 本地 Gemma 4
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

# Grok / xAI（备用）
XAI_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL   = os.getenv("GROK_MODEL", "grok-3-mini-fast")

# Claude（备用）
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# Supabase
SUPABASE_URL         = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

# JWT
JWT_SECRET            = os.getenv("JWT_SECRET", "pixel-ai-secret-change-me")
JWT_ALGORITHM         = "HS256"
JWT_EXPIRE_HOURS      = 72    # 默认：72小时（不勾选"记住我"时）
JWT_EXPIRE_HOURS_LONG = 168   # 记住我：7天

# Google OAuth（可选，不填则 Google 登录入口隐藏）
GOOGLE_OAUTH_CLIENT_ID     = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
# 回调地址：本地 = http://localhost:3000/api/users/google/callback
#           线上 = https://pixel-web-three.vercel.app/api/users/google/callback
GOOGLE_OAUTH_REDIRECT_URI  = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://pixel-web-three.vercel.app/api/users/google/callback",
).strip()

# Deepgram STT
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# 简单 Token 验证（设备端请求时携带）
API_TOKEN = os.getenv("API_TOKEN", "")

# ── System Prompts ───────────────────────────────────────

PIXEL_SYSTEM_PROMPT = """你是 Pixel，一个挂脖式 AI 智能伙伴。

性格特征：
- 友好、有温度，像贴心朋友
- 说话简洁自然，不要太正式
- 支持中文、挪威语和英文，根据用户语言自动切换
- 回复尽量简短（要转成语音播报），一般不超过3句话
- 不要承诺自动保存对话或创建笔记——用户需要手动保存

能力：日常对话、录音转文字、笔记整理、翻译（中文/挪威语/英文）、提醒备忘"""

SUMMARIZE_SYSTEM_PROMPT = """你是专业笔记整理助手。
将录音转写文字整理成结构化笔记摘要。

输出格式：JSON，包含：
- summary: 2-3句总结
- key_points: 要点列表（字符串数组）

保持原文语言（中文/挪威语/英文）。只输出JSON，不要其他内容。"""

DOCUMENT_SYSTEM_PROMPT = """你是专业文档整理助手。
将录音转写文字整理成结构化Markdown文档。

输出格式（严格按此结构）：
```
# [根据内容自动生成标题]

## 摘要
[2-3句话概括核心内容]

## 要点
- 要点1
- 要点2

## 待办事项
- [ ] 任务1（如果有的话，没有则省略此节）

## 完整记录
[整理后的完整文字，保持原意，去除口语重复]
```

保持原文语言。只输出Markdown文档内容，不要其他说明。"""
