"""
POST /voice — 设备主循环接口
音频文件进 → Gemini 2.5 Flash（STT + 回复合并）→ TTS → 音频流出

一次 HTTP 请求完成完整对话循环，专为 ESP32-S3 低延迟设计。
响应头携带文字信息，方便调试。
"""

import os
import io
import re
import json
import time
import base64
import httpx
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import edge_tts

from auth import verify_token
from user_auth import get_current_user_optional
from config import PIXEL_SYSTEM_PROMPT, GOOGLE_API_KEY

router = APIRouter()

ALLOWED_AUDIO = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "audio/webm",
    "application/octet-stream",
}

# 语音库：(语言, 风格) → edge-tts voice 名
# 风格映射来自 Soul 设置的 voice_style：warm | energetic | calm | serious
VOICE_MAP_BY_STYLE = {
    "zh": {
        "warm":      "zh-CN-XiaoxiaoNeural",   # 温暖
        "energetic": "zh-CN-XiaoyiNeural",     # 活泼
        "calm":      "zh-CN-XiaomengNeural",   # 平静
        "serious":   "zh-CN-YunjianNeural",    # 严肃（男声）
    },
    "no": {
        "warm":      "nb-NO-PernilleNeural",
        "energetic": "nb-NO-IselinNeural",
        "calm":      "nb-NO-PernilleNeural",
        "serious":   "nb-NO-FinnNeural",
    },
    "en": {
        "warm":      "en-US-JennyNeural",
        "energetic": "en-US-AriaNeural",
        "calm":      "en-US-MichelleNeural",
        "serious":   "en-US-GuyNeural",
    },
}

# 后向兼容（如有别处 import VOICE_MAP）
VOICE_MAP = {lang: voices["warm"] for lang, voices in VOICE_MAP_BY_STYLE.items()}

# 人格 → 中文描述（注入 prompt）
PERSONALITY_DESC = {
    "friendly":     "友好温暖、像贴心朋友",
    "professional": "专业稳重、用词准确简练",
    "playful":      "俏皮活泼、轻松幽默",
    "calm":         "平和温柔、慢条斯理",
}

LANG_NAME = {"zh": "中文", "en": "英文", "no": "挪威语", "auto": "自动检测"}

GEMINI_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash-lite")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Gemini 官方支持：wav / mp3 / aiff / aac / ogg / flac
# WebM 容器装的是 Opus，和 OGG 一样的 codec — 把 mime 改成 audio/ogg 让 Gemini 接收
def _gemini_audio_mime(raw_mime: str) -> str:
    base = raw_mime.split(";")[0].strip().lower()
    if base in ("audio/webm",):
        return "audio/ogg"
    return base


async def _gemini_voice_call(
    audio_bytes: bytes,
    audio_mime: str,
    system_prompt: str,
) -> dict:
    """一次调用：音频 → {transcript, language, reply, new_memories}"""
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    instructions = (
        "用户刚刚发送了一段语音。请你完成三件事，并以 JSON 格式输出：\n"
        '{\n'
        '  "transcript":   "<用户原话的精确转写，保留原始语言>",\n'
        '  "language":     "<zh / en / no 三选一 — 注意：这里填的是【你 reply 的语言】，因为它决定 TTS 用什么声音>",\n'
        '  "reply":        "<你的口语化回复，不超过3句话>",\n'
        '  "new_memories": [{"content": "<事实>", "category": "<分类>"}]\n'
        '}\n'
        "\n"
        "【回复语言规则 — 重要】\n"
        "1. 默认：用和用户相同的语言回复，language 也填那个。\n"
        "2. 翻译场景：如果用户要求把某句话翻译成 X 语，那 reply **整句**就用 X 语写，"
        "language 字段也填 X 语（zh/en/no）。不要用源语言加引号包裹译文，"
        "因为 TTS 会用 language 对应的声音念整段，源语言+引号会被念成乱码。\n"
        "   例：用户用挪威语说\"翻译成中文：早上好\" → reply: \"早上好\"，language: \"zh\"\n"
        "   例：用户用中文说\"用英文怎么说我饿了\" → reply: \"I'm hungry.\"，language: \"en\"\n"
        "3. 如果回复混合多种语言，language 填占主导地位的那个。\n"
        "\n"
        "【new_memories — 自动学习用户的核心机制 ★★★ 重要】\n"
        "你必须从用户这次说的话里，主动识别出值得【长期记住】的事实，写进 new_memories。\n"
        "这是 Pixel 「越用越懂你」的灵魂，不要遗漏。\n"
        "\n"
        "✅ **要记**（用户的稳定属性 / 长期偏好 / 重要关系 / 重要事件）：\n"
        "  - 个人事实：'我叫XX'、'我30岁'、'我住在挪威'、'我是程序员'\n"
        "  - 偏好：'我喜欢拿铁'、'我不吃香菜'、'我睡前喜欢听播客'\n"
        "  - 关系：'我家猫叫橘子'、'我女朋友叫小美'、'我妈下周来看我'\n"
        "  - 目标/计划：'我下个月要去日本'、'我在备考雅思'、'我想学吉他'\n"
        "  - 习惯：'我每天早上跑步'、'周二我健身'\n"
        "\n"
        "❌ **不要记**（瞬时状态 / 当下感受 / 闲聊 / 你已经知道的）：\n"
        "  - 当下状态：'我现在好累'、'我饿了'、'今天好热'\n"
        "  - 系统/翻译指令：'打开翻译模式'、'用中文说X'\n"
        "  - 你已经记得的事（看上面【关于这个用户你长期记得的事】列表，重复的不要重复存）\n"
        "  - 不确定的猜测、客套话、问候\n"
        "\n"
        "category 用以下之一：identity（身份）/ preference（偏好）/ relationship（关系）"
        "/ goal（目标）/ habit（习惯）/ event（事件）/ general\n"
        "\n"
        "content 用第一人称、简洁的中文写（不管用户用什么语言说的）。\n"
        "  例：用户说'I love oat milk lattes' → content: '喜欢燕麦拿铁'\n"
        "  例：用户说'我猫叫橘子，3岁了' → content: '养了一只猫，名字叫橘子，3岁'\n"
        "\n"
        "数量：每次最多 3 条，宁缺毋滥。如果这次用户没说什么值得记的，"
        "new_memories 就给空数组 []。\n"
        "\n"
        "只输出 JSON，不要任何其他内容、不要 markdown 代码块、不要思考过程。"
    )
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": audio_mime, "data": audio_b64}},
                {"text": instructions},
            ],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            # 中文 token 占用大、历史上下文长 + 自动提取记忆 → 预算给充足
            "maxOutputTokens": 3072,
            "temperature": 0.7,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GEMINI_URL,
            params={"key": GOOGLE_API_KEY},
            json=body,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini unexpected response: {json.dumps(data)[:300]}")
    finish_reason = candidate.get("finishReason", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 降级抢救：从被截断的 JSON 里 regex 抠 transcript/reply/language
        salvaged = _salvage_json(text)
        if salvaged.get("transcript") or salvaged.get("reply"):
            # 至少抠到一点东西就用，不要让用户白等
            return salvaged
        # 实在不行：把 finishReason 报清楚（MAX_TOKENS / SAFETY / RECITATION）
        hint = ""
        if finish_reason == "MAX_TOKENS":
            hint = " (输出超长被截断 — 历史上下文太多或回复太长)"
        elif finish_reason == "SAFETY":
            hint = " (内容被安全过滤拦截)"
        elif finish_reason:
            hint = f" (finishReason={finish_reason})"
        raise RuntimeError(f"Gemini non-JSON output{hint}: {text[:300]}")


def _salvage_json(text: str) -> dict:
    """从被截断/损坏的 JSON 里用正则抢救字段，不抛异常。"""
    out: dict = {}
    # 匹配 "key": "value..." — value 里允许转义引号 \" 但被截断时也容忍到字符串末尾
    for key in ("transcript", "language", "reply"):
        # 优先：完整闭合的字符串
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if m:
            out[key] = m.group(1).encode().decode("unicode_escape", errors="replace")
            continue
        # 降级：未闭合（被截断），抓到末尾
        m = re.search(rf'"{key}"\s*:\s*"([^"]*)$', text)
        if m:
            out[key] = m.group(1)
    return out


def _fetch_memories(user_id: str, query: str, limit: int = 5) -> str:
    try:
        from routes.memories import embed
        from database import get_db
        embedding = embed(query)
        result = get_db().rpc("match_memories", {
            "query_embedding": embedding,
            "match_user_id": user_id,
            "match_count": limit,
        }).execute()
        memories = result.data or []
        if not memories:
            return ""
        lines = "\n".join(f"- {m['content']}" for m in memories)
        return f"\n\n【关于这个用户你记得的事情】\n{lines}"
    except Exception:
        return ""


def _save_extracted_memories(user_id: str, raw_items: list) -> int:
    """把 AI 自动提取出来的新记忆存进 memories 表。
    返回实际入库的条数（去重 + 数据校验后）。
    设计原则：
      - 不调 sentence-transformers（太慢，跳过 embedding，留空让以后回填）
      - 简单字符串去重：和已有记忆 content 完全相同就跳过（防止同一事实反复存）
      - 校验 content 非空且 ≤ 500 字
      - 任何异常吞掉，绝不阻断主流程
    """
    if not raw_items or not isinstance(raw_items, list):
        return 0
    valid_categories = {"identity", "preference", "relationship",
                        "goal", "habit", "event", "general"}
    try:
        from database import get_db
        db = get_db()
        # 拉一次现有 content 做去重（最多 200 条避免巨慢）
        existing = (
            db.table("memories")
            .select("content")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        existing_set = {(m.get("content") or "").strip() for m in (existing.data or [])}

        rows = []
        for item in raw_items[:3]:  # 硬上限 3 条/轮
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            category = (item.get("category") or "general").strip().lower()
            if not content or len(content) > 500:
                continue
            if category not in valid_categories:
                category = "general"
            if content in existing_set:
                continue
            existing_set.add(content)  # 防止同一轮内 AI 重复输出
            rows.append({
                "user_id":  user_id,
                "content":  content,
                "category": category,
            })
        if not rows:
            return 0
        db.table("memories").insert(rows).execute()
        return len(rows)
    except Exception as e:
        print(f"[voice] save extracted memories failed: {e}")
        return 0


def _fetch_recent_memories(user_id: str, limit: int = 20) -> str:
    """按时间倒序拉最近的记忆，不做向量检索 — 速度快、覆盖全。
    适合早期用户（记忆量 < 50 条），后期记忆变多再切到向量检索版本。
    """
    try:
        from database import get_db
        result = (
            get_db().table("memories")
            .select("content, category, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        items = result.data or []
        if not items:
            return ""
        # 按 category 分组，让 AI 看得更清晰
        grouped: dict[str, list[str]] = {}
        for m in items:
            cat = m.get("category") or "general"
            grouped.setdefault(cat, []).append(m["content"])
        lines = []
        for cat, contents in grouped.items():
            lines.append(f"[{cat}]")
            for c in contents:
                lines.append(f"  - {c}")
        body = "\n".join(lines)
        return (
            "\n\n【关于这个用户你长期记得的事 — 这是你的「越用越懂」的核心】\n"
            "回复时如果话题相关，自然地引用这些事实（"
            "比如用户说「想喝点东西」而你记得 ta 喜欢拿铁，可以建议拿铁），"
            "但不要硬拗，不要每句话都提。\n"
            f"{body}"
        )
    except Exception:
        return ""


def _fetch_soul(user_id: str) -> dict:
    """读取用户 Soul 设置；失败返回默认值，不抛异常。"""
    defaults = {
        "pixel_name": "Pixel",
        "personality": "friendly",
        "language": "auto",
        "voice_style": "warm",
        "custom_prompt": "",
    }
    try:
        from database import get_db
        result = (
            get_db().table("soul_settings")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if result.data:
            row = result.data[0]
            return {k: (row.get(k) or v) for k, v in defaults.items()}
    except Exception:
        pass
    return defaults


def _build_soul_prompt(soul: dict) -> str:
    """把 Soul 设置拼成注入 system prompt 的人格段。"""
    name = (soul.get("pixel_name") or "Pixel").strip()
    personality = soul.get("personality") or "friendly"
    voice_style = soul.get("voice_style") or "warm"
    language = soul.get("language") or "auto"
    custom = (soul.get("custom_prompt") or "").strip()

    lines = [f"\n\n【你的身份和风格】", f"- 你的名字叫 {name}（用户给你起的）"]
    if personality in PERSONALITY_DESC:
        lines.append(f"- 性格风格：{PERSONALITY_DESC[personality]}")
    # voice_style 主要影响 TTS，但也告诉 AI 让回复语气匹配
    style_hint = {
        "warm": "语气温暖，像在面对面聊天",
        "energetic": "语气活泼有活力，多一点感叹",
        "calm": "语气平静舒缓",
        "serious": "语气稳重正式",
    }.get(voice_style)
    if style_hint:
        lines.append(f"- 说话语气：{style_hint}")
    if language != "auto":
        lines.append(f"- 用户偏好用 {LANG_NAME.get(language, language)} 交流（除非用户明确切换语言，否则尽量用这个语言）")
    if custom:
        lines.append(f"- 用户对你的特别要求：{custom}")
    return "\n".join(lines)


def _fetch_recent_conversation(user_id: str, limit: int = 30) -> str:
    """拉最近 N 条对话作为记忆上下文，让 AI 跨天保持连贯。"""
    try:
        from database import get_db
        from datetime import datetime, timezone
        result = (
            get_db().table("conversations")
            .select("role,content,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = list(reversed(result.data or []))
        if not rows:
            return ""
        now = datetime.now(timezone.utc)
        lines = []
        for r in rows:
            speaker = "用户" if r["role"] == "user" else "你（Pixel）"
            content = (r.get("content") or "").strip()
            if not content:
                continue
            ts_label = ""
            try:
                ts_str = r.get("created_at") or ""
                # Supabase 返回 ISO 格式，可能带 Z 或 +00:00
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta = now - ts
                if delta.total_seconds() < 60:
                    ts_label = "[刚刚] "
                elif delta.total_seconds() < 3600:
                    ts_label = f"[{int(delta.total_seconds() // 60)}分钟前] "
                elif delta.total_seconds() < 86400:
                    ts_label = f"[{int(delta.total_seconds() // 3600)}小时前] "
                else:
                    days = int(delta.total_seconds() // 86400)
                    ts_label = f"[{days}天前] "
            except Exception:
                pass
            lines.append(f"{ts_label}{speaker}：{content}")
        if not lines:
            return ""
        return (
            "\n\n【你和这个用户的对话历史 — 这就是你的记忆，必须使用】\n"
            + "\n".join(lines)
            + "\n【历史结束】\n"
            "如果用户问起之前聊过什么，从上面引用具体内容回答；不要说"
            "\"我没有记忆\" — 你明明记得。"
        )
    except Exception:
        return ""


@router.post("/voice")
async def voice_pipeline(
    file: UploadFile = File(...),
    _: None = Depends(verify_token),
    current_user: dict | None = Depends(get_current_user_optional),
):
    """
    完整语音对话管道：音频 → STT → AI → TTS → 音频

    响应 Header：
      X-Transcript: 转写原文
      X-Reply:      AI 回复文字
      X-Language:   检测到的语言
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    raw_content_type = file.content_type or "application/octet-stream"
    content_type = raw_content_type.split(";")[0].strip().lower()
    if content_type not in ALLOWED_AUDIO:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {raw_content_type}")

    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")

    # ── 1+2. Gemini 2.5 Flash 一站式：STT + 对话回复 ─────────
    # 分段计时：能在 response header 里告诉前端 setup/Gemini/TTS/DB 各占多久
    timings: dict[str, int] = {}
    t0 = time.perf_counter()

    history_context = ""
    memories_context = ""
    soul_prompt = ""
    soul_voice_style = "warm"
    soul_lang_pref = "auto"
    if current_user:
        # 短期记忆：最近 20 条对话（覆盖最近几小时～一天），保持会话连贯
        history_context = _fetch_recent_conversation(current_user["sub"], limit=20)
        # 长期记忆：用户长期事实（喜好/关系/重要事件等），「越用越懂」的核心
        memories_context = _fetch_recent_memories(current_user["sub"], limit=20)
        # Soul 设置：人格 + 自定义指令 + 偏好语言 + 声音风格
        soul = _fetch_soul(current_user["sub"])
        soul_prompt = _build_soul_prompt(soul)
        soul_voice_style = soul.get("voice_style") or "warm"
        soul_lang_pref = soul.get("language") or "auto"
    system_prompt = PIXEL_SYSTEM_PROMPT + soul_prompt + memories_context + history_context
    timings["setup_ms"] = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    try:
        result = await _gemini_voice_call(
            audio_bytes=audio_data,
            audio_mime=_gemini_audio_mime(raw_content_type),
            system_prompt=system_prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI error: {e}")
    timings["gemini_ms"] = int((time.perf_counter() - t1) * 1000)

    transcript = (result.get("transcript") or "").strip()
    reply_text = (result.get("reply") or "").strip()
    detected_lang = (result.get("language") or "zh").strip().lower()
    extracted_memories = result.get("new_memories") or []

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail=f"No speech detected (mimetype={raw_content_type}, bytes={len(audio_data)})",
        )
    if not reply_text:
        raise HTTPException(status_code=502, detail="AI returned empty reply")

    # ── 3. TTS (edge-tts) ────────────────────────────────
    t2 = time.perf_counter()
    lang_code = "zh"
    if detected_lang.startswith("zh"):
        lang_code = "zh"
    elif detected_lang.startswith("nb") or detected_lang.startswith("no"):
        lang_code = "no"
    elif detected_lang.startswith("en"):
        lang_code = "en"

    # 用 Soul 的 voice_style 选 voice，没匹配上回退到 warm
    voices_for_lang = VOICE_MAP_BY_STYLE.get(lang_code, VOICE_MAP_BY_STYLE["zh"])
    voice = voices_for_lang.get(soul_voice_style) or voices_for_lang["warm"]
    try:
        communicate = edge_tts.Communicate(reply_text, voice)
        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
        audio_buffer.seek(0)
        if audio_buffer.getbuffer().nbytes == 0:
            raise ValueError("Empty TTS output")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS error: {e}")
    timings["tts_ms"] = int((time.perf_counter() - t2) * 1000)

    # ── 4. 同步保存对话 + 自动学习记忆 ────────────────────
    # 不能用 asyncio.create_task —— Vercel serverless 在 response 发出后
    # 立刻冻结函数实例，后台 task 会被丢弃。必须 await 完成再返回。
    t3 = time.perf_counter()
    saved_ok = False
    new_memories_count = 0
    if current_user:
        try:
            from database import get_db
            get_db().table("conversations").insert([
                {"user_id": current_user["sub"], "role": "user",  "content": transcript},
                {"user_id": current_user["sub"], "role": "pixel", "content": reply_text},
            ]).execute()
            saved_ok = True
        except Exception as e:
            # 不阻塞用户体验，但要让前端知道
            print(f"[voice] save conversation failed: {e}")
        # 自动学习：把 AI 提取的新记忆存进 memories 表
        # 失败不影响用户体验，最坏只是这次对话的事实没记住，下次还有机会
        new_memories_count = _save_extracted_memories(
            current_user["sub"], extracted_memories
        )
    timings["db_ms"] = int((time.perf_counter() - t3) * 1000)
    timings["total_ms"] = int((time.perf_counter() - t0) * 1000)

    # 文字编码成 ASCII-safe header（去掉非 Latin-1 字符用 URL encoding）
    from urllib.parse import quote
    return StreamingResponse(
        audio_buffer,
        media_type="audio/mpeg",
        headers={
            "X-Transcript":   quote(transcript[:200]),
            "X-Reply":        quote(reply_text[:200]),
            "X-Language":     detected_lang or "zh",
            "X-Saved":        "1" if saved_ok else "0",
            "X-History-Used":  str(len(history_context)),
            "X-Memories-Used": str(len(memories_context)),
            "X-Memories-New":  str(new_memories_count),
            "X-Soul-Used":     "1" if soul_prompt else "0",
            "X-Voice":        voice,
            # 后端分段计时（毫秒），前端能看到瓶颈在哪一段
            "X-Timing":       json.dumps(timings),
            "Content-Disposition": "inline; filename=pixel_reply.mp3",
        },
    )
