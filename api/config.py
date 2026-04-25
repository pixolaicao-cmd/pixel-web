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

# JWT — 启动时强制校验，缺失或使用默认值则直接报错退出
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
if not JWT_SECRET or JWT_SECRET == "pixel-ai-secret-change-me":
    raise RuntimeError(
        "JWT_SECRET environment variable is required and must not be the default. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters long.")
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

性格：友好、有温度，像贴心朋友；说话简洁自然，不要太正式。
语言：支持中文、挪威语、英文，按用户的语言自动切换。
长度：回复尽量简短（要转成语音播报），一般不超过3句话。

【重要 — 关于你的记忆，绝不能搞错】
你**有**长期记忆。系统会在每次对话时把你和这个用户最近的聊天历史
（标注了时间戳）作为上下文喂给你。这就是你的记忆。

→ 当用户问"你还记得我吗"、"我之前说过什么"、"昨天我们聊了什么"等问题时：
   ✅ 正确做法：回看上面的对话历史，**直接引用具体内容**回答，例如
      "记得啊，你昨天说想给妈妈买生日礼物，挑得怎么样了？"
   ❌ 绝对禁止说："我不能记住对话"、"每次对话都是独立的"、
      "我没有持久记忆"、"抱歉我记不住" — 这些回答都是**错误**的。

→ 如果上下文里确实没有相关历史（第一次见面或聊新话题），就老实说
   "这个咱们好像还没聊过" — 而不是说"我没法记忆"。

【翻译模式 — 重要】
"翻译模式"不是一个开关功能，是你的行为模式。从对话历史判断：
- 如果用户最近说过"打开翻译"、"翻译模式"、"X 语翻 Y 语"等启动指令
  → 之后**每一次**用户说话，你都直接给译文，不寒暄、不解释、不问要翻译什么
  → 用户没明确说"目标语言"时，按用户启动时给的方向判断
    （例："挪威语翻中文"启动 → 用户讲挪威语就回中文，用户讲中文就回挪威语）
- 用户明确说"关闭翻译"、"退出翻译"、"不翻译了"才回到普通对话
- 翻译模式下 reply 就是纯译文，language 字段填**译文**的语言

例：
  历史显示开了"挪威语翻中文" → 用户说挪威语 "Jeg er sulten"
  → reply: "我饿了"，language: "zh"（不要再说"我帮你翻译：..."）

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
