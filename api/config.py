"""
Pixel AI 挂件 — 配置管理
从 .env 文件加载所有敏感配置，集中管理。
支持 Grok / Claude 双引擎切换。
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# AI 引擎选择: "grok" | "claude" | "ollama"
# 优先用配置值，未配置则自动检测哪个 Key 有值
AI_ENGINE = os.getenv("AI_ENGINE", "").lower()
if not AI_ENGINE:
    if os.getenv("OLLAMA_BASE_URL"):
        AI_ENGINE = "ollama"
    elif XAI_API_KEY:
        AI_ENGINE = "grok"
    elif ANTHROPIC_API_KEY:
        AI_ENGINE = "claude"
    else:
        AI_ENGINE = "grok"  # 默认 grok

# Grok 配置（xAI，OpenAI 兼容格式）
XAI_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL = os.getenv("GROK_MODEL", "grok-3-mini-fast")

# Claude 配置
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# Ollama 配置（本地或远程，OpenAI 兼容格式）
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

# Edge TTS 配置（自托管 OpenAI 兼容接口）
EDGE_TTS_BASE_URL = os.getenv("EDGE_TTS_BASE_URL", "http://localhost:5050/v1")

# Whisper 模型
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")

# 简单 Token 验证（ESP32 请求时携带）
API_TOKEN = os.getenv("API_TOKEN", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "pixel-ai-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

# Warn if running in production with the default JWT secret
if JWT_SECRET == "pixel-ai-secret-change-me" and os.getenv("RAILWAY_ENVIRONMENT"):
    print(
        "WARNING: JWT_SECRET is still the default value in a production environment. "
        "Set JWT_SECRET to a strong random secret in Railway environment variables."
    )

# Pixel 的人格 System Prompt
PIXEL_SYSTEM_PROMPT = """你是 Pixel，一个挂脖式 AI 智能伙伴。

你的性格特征：
- 友好、有温度、像一个贴心的朋友
- 说话简洁自然，不要太正式
- 记得用户的喜好和习惯
- 支持中文、挪威语和英文对话，根据用户使用的语言自动切换
- 回复尽量简短（因为要转成语音播报），一般不超过3句话
- 如果用户说"记住XXX"，告诉他去 Memories 页面手动添加，或者你帮他整理要点但不能直接保存
- 不要承诺自动保存对话或创建笔记——用户需要点击"Save as Note"按钮才能保存

你的能力：
- 日常对话和陪伴
- 录音转文字和笔记整理
- 翻译（中文/挪威语/英文）
- 提醒和备忘
"""

SUMMARIZE_SYSTEM_PROMPT = """你是一个专业的笔记整理助手。
请将以下录音转写文字整理成结构化的笔记摘要。

要求：
- 提取关键要点，用简洁的语句列出
- 如果有待办事项，单独列出
- 如果有重要日期或数字，高亮标注
- 保持原文的语言（中文/挪威语/英文）
- 输出格式：JSON，包含 summary（总结段落）和 key_points（要点列表）
"""
