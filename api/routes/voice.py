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
import asyncio
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
# 固件多 part 上传偶尔会丢 Content-Type 退化成 application/octet-stream — 默认按 wav 处理（固件录的就是 WAV）
GEMINI_SUPPORTED_AUDIO = {
    "audio/wav", "audio/mpeg", "audio/mp3",
    "audio/aiff", "audio/aac", "audio/ogg", "audio/flac",
}

def _gemini_audio_mime(raw_mime: str) -> str:
    base = (raw_mime or "").split(";")[0].strip().lower()
    if base == "audio/webm":
        return "audio/ogg"
    if base in GEMINI_SUPPORTED_AUDIO:
        return base
    # 兜底：octet-stream / 空 / 未知 → 当 wav（固件 & web 端目前都送 wav）
    return "audio/wav"


async def _gemini_voice_call(
    audio_bytes: bytes,
    audio_mime: str,
    system_prompt: str,
    translation_mode: bool = False,
    translation_lang_a: str | None = None,
    translation_lang_b: str | None = None,
) -> dict:
    """一次调用：音频 → {transcript, language, reply, new_memories}"""
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

    # 翻译模式 — 必须在 instructions 头部强制，否则会被下面的"默认相同语言"覆盖。
    # 这是用户开了 chip / dashboard / 语音触发后必须遵守的最高优先级规则。
    translation_block = ""
    if translation_mode and translation_lang_a and translation_lang_b:
        a_name = LANG_NAME.get(translation_lang_a, translation_lang_a)
        b_name = LANG_NAME.get(translation_lang_b, translation_lang_b)
        translation_block = (
            "\n\n【⚠️ 当前翻译模式已开启 — 这是最高优先级规则，覆盖下面所有"
            "「相同语言回复」的默认行为】\n"
            f"- 用户讲 {a_name}（{translation_lang_a}）→ reply 必须**只**用 "
            f"{b_name}（{translation_lang_b}）写译文\n"
            f"- 用户讲 {b_name}（{translation_lang_b}）→ reply 必须**只**用 "
            f"{a_name}（{translation_lang_a}）写译文\n"
            "- reply 字段填**纯译文**，不要寒暄、不要解释、不要任何前缀（"
            '不要说"翻译过来是"、"你说的是"、"好的"）\n'
            f"- language 字段填**译文**的语言代码（{translation_lang_a} 或 "
            f"{translation_lang_b}）\n"
            "- 不要因为用户说「你好」「谢谢」就回复闲聊 — 翻译模式下连寒暄"
            "都翻译\n"
            "- 仅当用户明确说「关闭翻译」「退出翻译」「stop translation」之类"
            "才退出此模式（系统会自行处理状态切换，你照常输出译文即可）\n"
        )

    instructions = (
        "用户刚刚发送了一段语音。请你完成三件事，并以 JSON 格式输出：\n"
        '{\n'
        '  "transcript":   "<用户原话的精确转写，保留原始语言>",\n'
        '  "language":     "<zh / en / no 三选一 — 注意：这里填的是【你 reply 的语言】，因为它决定 TTS 用什么声音>",\n'
        '  "reply":        "<你的口语化回复，不超过3句话>",\n'
        '  "new_memories": [{"content": "<事实>", "category": "<分类>"}]\n'
        '}\n'
        + translation_block +
        "\n"
        "【回复语言规则 — 重要】\n"
        + ("（注意：上面【翻译模式】规则覆盖此节，翻译模式下整段忽略下面的「相同语言」默认）\n"
           if translation_block else "") +
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
            # 回复 ≤3 句话 + transcript 短 + 最多 3 条记忆 → 1024 足够
            # 上限调小不直接降延迟，但能让 Gemini 路由器更早出 token、降低被截断风险
            "maxOutputTokens": 1024,
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
        "recording_mode": False,
        "translation_mode": False,
        "translation_lang_a": None,
        "translation_lang_b": None,
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
            # bool 字段不能用 `or v` 融合（False 会被回退成默认）；
            # 语言字段可以是 None
            BOOL_KEYS = {"recording_mode", "translation_mode"}
            NULLABLE_KEYS = {"translation_lang_a", "translation_lang_b"}
            merged = {}
            for k, v in defaults.items():
                raw = row.get(k)
                if k in BOOL_KEYS:
                    merged[k] = bool(raw) if raw is not None else v
                elif k in NULLABLE_KEYS:
                    merged[k] = raw  # 允许 None
                else:
                    merged[k] = raw or v
            return merged
    except Exception:
        pass
    return defaults


# ── 记录模式开关：通过语音指令触发 ─────────────────────────
# 触发短语 — 大小写/标点不敏感，只要 transcript 包含其中之一就视为指令
RECORDING_ON_PHRASES = [
    # 中文 — 正式（"开始/打开/开" 三种前缀）
    "开始记录", "开始保存", "开始录", "记录开始", "保存开始",
    "开始录音", "开始录下来", "录起来", "开始录起来",
    "打开记录", "打开录音", "打开记录功能", "打开录音功能",
    "开记录", "开录音", "开启记录", "开启录音",
    # 中文 — 口语化（用户实测说"录音"、"录一下"也算触发）
    "录音", "录下来", "录一下", "录一段",
    "记下来", "记一下", "帮我记", "帮我录",
    "保存对话", "保存这段", "保存这次",
    "把这段录下来", "把它录下来", "把这段记下来",
    # English
    "start recording", "start saving", "begin recording",
    "record this", "save this", "save the conversation",
    "turn on recording", "enable recording",
    # Norsk
    "start ta opp", "begynn å lagre", "ta opp dette", "lagre samtalen",
    "skru på opptak", "slå på opptak",
]
RECORDING_OFF_PHRASES = [
    # 中文 — 正式
    "停止记录", "停止保存", "停止录", "结束记录", "结束保存",
    "停止录音", "结束录音", "关闭记录", "关闭录音",
    "关闭记录功能", "关闭录音功能", "关掉记录", "关掉录音",
    # 中文 — 口语化
    "不要记录了", "别记录了", "别记了", "别录了", "不录了", "不记了",
    "不用录了", "不用记了", "停下", "够了 别录了",
    # English
    "stop recording", "stop saving", "end recording",
    "stop the recording", "don't record",
    "turn off recording", "disable recording",
    # Norsk
    "stopp opptak", "slutt å lagre", "stopp innspilling",
    "skru av opptak", "slå av opptak",
]


# ── 翻译模式开关：通过语音指令触发 ─────────────────────────
# 翻译模式是双向：用户讲 lang_a → 回 lang_b；讲 lang_b → 回 lang_a。
# 触发短语里要能解析出语言对（中-挪 / 中-英 / 英-挪）。
TRANSLATION_OFF_PHRASES = [
    # 中文
    "关闭翻译", "退出翻译", "停止翻译", "不要翻译了", "别翻译了",
    "关掉翻译", "关闭翻译模式", "退出翻译模式",
    # English
    "stop translation", "stop translating", "exit translation",
    "turn off translation", "disable translation",
    # Norsk
    "stopp oversettelse", "avslutt oversettelse",
]
# ON 触发关键词（任意一个 + 至少两种语言名 → 进入翻译模式）
TRANSLATION_ON_KEYWORDS = [
    "翻译", "互译", "翻一下",
    "translate", "translation",
    "oversett", "oversettelse",
]
# 语言名 → 标准代码（中文需要先识别，再判断 lang_a/lang_b）
LANG_ALIASES = {
    "zh": ["中文", "中国话", "汉语", "普通话", "国语", "chinese", "mandarin", "kinesisk"],
    "no": ["挪威", "挪威语", "挪威话", "norwegian", "norsk", "bokmål", "nynorsk"],
    "en": ["英文", "英语", "english", "engelsk"],
}


def _detect_translation_off(transcript: str) -> bool:
    if not transcript:
        return False
    lower = transcript.lower()
    return any(p.lower() in lower for p in TRANSLATION_OFF_PHRASES)


def _detect_translation_on(transcript: str) -> tuple[str, str] | None:
    """
    检测翻译开启指令并解析语言对。
    返回 (lang_a, lang_b) 或 None。
    例：「打开中文挪威语翻译」→ ("zh", "no")
        「我说中文你说挪威语」→ ("zh", "no")
    规则：
      - 必须命中至少一个 TRANSLATION_ON_KEYWORDS 才算开启意图
      - 然后从 transcript 里抓两种不同的语言（按出现顺序，第一个=lang_a）
    """
    if not transcript:
        return None
    lower = transcript.lower()
    # 不是开启意图就不进
    if not any(kw.lower() in lower for kw in TRANSLATION_ON_KEYWORDS):
        return None
    # 在 transcript 里找语言名出现的位置
    found: list[tuple[int, str]] = []  # (位置, 语言代码)
    for code, aliases in LANG_ALIASES.items():
        for alias in aliases:
            idx = lower.find(alias)
            if idx >= 0:
                found.append((idx, code))
                break  # 同一语言只记第一次
    if len(found) < 2:
        return None
    # 按出现顺序取头两个不同语言
    found.sort()
    seen: list[str] = []
    for _, code in found:
        if code not in seen:
            seen.append(code)
        if len(seen) == 2:
            break
    if len(seen) < 2:
        return None
    return (seen[0], seen[1])


def _set_translation_mode(
    user_id: str,
    enabled: bool,
    lang_a: str | None = None,
    lang_b: str | None = None,
) -> bool:
    """落库 translation_mode + 语言对。失败不抛。"""
    try:
        from database import get_db
        payload: dict = {
            "user_id": user_id,
            "translation_mode": enabled,
        }
        # 关闭时清空语言对（避免下次开启被旧值污染判定）
        if enabled:
            payload["translation_lang_a"] = lang_a
            payload["translation_lang_b"] = lang_b
        else:
            payload["translation_lang_a"] = None
            payload["translation_lang_b"] = None
        get_db().table("soul_settings").upsert(
            payload, on_conflict="user_id"
        ).execute()
        return True
    except Exception as e:
        print(f"[voice] set translation_mode failed: {e}")
        return False


def _detect_recording_toggle(transcript: str) -> str | None:
    """
    扫描 transcript 是否包含开/关记录指令。
    返回 'on' / 'off' / None。

    设计：保持简单字符串匹配，比让 Gemini 输出额外字段更稳。
    用户说「我们开始记录这次会议」也能命中 — 这是预期行为。
    """
    if not transcript:
        return None
    lower = transcript.lower()
    # 关闭命令优先（避免「不要记录了，开始正常聊天」这类误判 → 应该是关）
    for phrase in RECORDING_OFF_PHRASES:
        if phrase.lower() in lower:
            return "off"
    for phrase in RECORDING_ON_PHRASES:
        if phrase.lower() in lower:
            return "on"
    return None


def _set_recording_mode(user_id: str, enabled: bool) -> bool:
    """落库 recording_mode；失败不抛，返回是否成功。"""
    try:
        from database import get_db
        # upsert：用户首次切换时 soul_settings 行可能还不存在
        get_db().table("soul_settings").upsert(
            {"user_id": user_id, "recording_mode": enabled},
            on_conflict="user_id",
        ).execute()
        return True
    except Exception as e:
        print(f"[voice] set recording_mode failed: {e}")
        return False


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

    # 翻译模式 — 强指令，盖过 system_prompt 的默认对话行为
    # （system_prompt 里的翻译段是回退方案；这里有明确状态时直接注入）
    if soul.get("translation_mode"):
        lang_a = soul.get("translation_lang_a")
        lang_b = soul.get("translation_lang_b")
        if lang_a and lang_b:
            a_name = LANG_NAME.get(lang_a, lang_a)
            b_name = LANG_NAME.get(lang_b, lang_b)
            lines.append("")
            lines.append("【⚠️ 翻译模式：当前激活】")
            lines.append(
                f"- 用户讲 {a_name} → 你只回 {b_name} 译文；"
                f"用户讲 {b_name} → 你只回 {a_name} 译文"
            )
            lines.append(
                f"- reply 字段填**纯译文**，不要寒暄、不要解释、不要前缀"
                f'（不要说"翻译过来是..."、"你说的是..."）'
            )
            lines.append(
                f"- language 字段填**译文**的语言代码（{lang_a} 或 {lang_b}）"
            )
            lines.append(
                "- 如果用户说的不是这两种语言（例如英文），保持当前模式 "
                "但用最接近的语言回译，并在脑内忽略此句不影响开关"
            )
    return "\n".join(lines)


def _fetch_recent_conversation(user_id: str, limit: int = 30) -> str:
    """拉最近 N 条对话作为记忆上下文，让 AI 跨天保持连贯。

    重要：不按 expires_at 过滤 — Pixel 需要看到全部最近对话（包括 24h 内的
    临时上下文 + 用户主动记录的永久档案），否则关闭 recording_mode 后会失忆。
    UI 端的过滤在 conversations.py 里做。
    """
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
    recording_was_on = False  # 进入这次请求时的状态，用于 toggle 判定
    translation_was_on = False
    translation_lang_a_was: str | None = None
    translation_lang_b_was: str | None = None
    if current_user:
        # 三个独立的 DB 拉取并行跑 — supabase-py 是同步的，丢线程池里 gather
        # 串行 ~300-450ms（3×单跳 RTT）→ 并行 ~150ms
        # limit 收紧：history 20→12、memories 20→15。用户实测如果上下文还不够再调。
        user_id = current_user["sub"]
        history_context, memories_context, soul = await asyncio.gather(
            asyncio.to_thread(_fetch_recent_conversation, user_id, 12),
            asyncio.to_thread(_fetch_recent_memories, user_id, 15),
            asyncio.to_thread(_fetch_soul, user_id),
        )
        soul_prompt = _build_soul_prompt(soul)
        soul_voice_style = soul.get("voice_style") or "warm"
        soul_lang_pref = soul.get("language") or "auto"
        recording_was_on = bool(soul.get("recording_mode"))
        translation_was_on = bool(soul.get("translation_mode"))
        translation_lang_a_was = soul.get("translation_lang_a")
        translation_lang_b_was = soul.get("translation_lang_b")
    system_prompt = PIXEL_SYSTEM_PROMPT + soul_prompt + memories_context + history_context
    timings["setup_ms"] = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    try:
        result = await _gemini_voice_call(
            audio_bytes=audio_data,
            audio_mime=_gemini_audio_mime(raw_content_type),
            system_prompt=system_prompt,
            translation_mode=translation_was_on,
            translation_lang_a=translation_lang_a_was,
            translation_lang_b=translation_lang_b_was,
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

    # ── 3. 选 TTS voice ──────────────────────────────────
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

    # ── 4. DB 写入改成「TTS 流式中并行」：
    # 之前是先 await 写完 → 再启 TTS（~300-500ms 全部计入首帧延迟）
    # 现在：在生成器里 create_task 开后台写，generator 结束前 await 它收尾。
    # generator 还在 yield → Vercel 函数实例不会被冻结 → 后台 task 安全完成。
    #
    # 记录模式逻辑：
    #   - 默认 OFF：闲聊只存 24h 临时上下文（expires_at = now + 24h）
    #   - 用户说 "开始记录" → 这一轮 + 之后所有轮都写永久档案 (expires_at = NULL)
    #   - 用户说 "停止记录" → 切回 24h 临时模式
    #   - memories 永远存（「越用越懂」的核心，不受 recording_mode 影响）
    toggle: str | None = None
    effective_recording = False
    new_state_to_persist: bool | None = None
    # 翻译模式 toggle —— 同样的双状态机：off > on（避免「不要翻译了，开始正常聊」误开）
    translation_toggle: str | None = None
    translation_state_to_persist: tuple[bool, str | None, str | None] | None = None
    effective_translation = False
    effective_translation_pair: tuple[str | None, str | None] = (None, None)
    if current_user:
        toggle = _detect_recording_toggle(transcript)
        if toggle == "on":
            effective_recording = True
        elif toggle == "off":
            effective_recording = False
        else:
            effective_recording = recording_was_on
        if toggle is not None:
            new_state = (toggle == "on")
            if new_state != recording_was_on:
                new_state_to_persist = new_state

        # 翻译模式 toggle：先检测关闭，再检测开启
        if _detect_translation_off(transcript):
            translation_toggle = "off"
            effective_translation = False
            effective_translation_pair = (None, None)
            if translation_was_on:
                translation_state_to_persist = (False, None, None)
        else:
            pair = _detect_translation_on(transcript)
            if pair is not None:
                translation_toggle = "on"
                effective_translation = True
                effective_translation_pair = pair
                # 状态变化条件：之前没开 / 之前开的语言对不一样
                if (not translation_was_on
                        or translation_lang_a_was != pair[0]
                        or translation_lang_b_was != pair[1]):
                    translation_state_to_persist = (True, pair[0], pair[1])
            else:
                # 没说翻译相关，沿用现有状态
                effective_translation = translation_was_on
                effective_translation_pair = (translation_lang_a_was, translation_lang_b_was)
    # db_ms 在这里只衡量「准备时间」（基本 0），真实写入耗时在 generator 里观测
    timings["db_ms"] = 0

    # ── 5. 流式 TTS：边生成边 yield ────────────────────────
    # tts_ms 在这个语义下表示「从启动 TTS 到第一个 audio chunk 的耗时」(TTFB)，
    # 不再是 TTS 全段完成时间。total_ms 同理代表「response 头发出之前的总耗时」。
    t2 = time.perf_counter()
    timings["total_ms"] = int((time.perf_counter() - t0) * 1000)
    # 注意：headers 必须在 generator yield 第一帧之前固化，所以 timings 在这里冻结。
    # 真正的 first-byte / TTS 时间可以在 generator 内补到 trailers，但 Vercel 不一定透传。

    def _persist_all_sync():
        """所有 DB 写入打包到一个同步函数里，扔线程池跑。
        失败吞掉只打日志 — 用户体验绝不阻塞、绝不出错。
        """
        try:
            if new_state_to_persist is not None and current_user:
                _set_recording_mode(current_user["sub"], new_state_to_persist)
            if translation_state_to_persist is not None and current_user:
                _enabled, _la, _lb = translation_state_to_persist
                _set_translation_mode(current_user["sub"], _enabled, _la, _lb)
            if current_user:
                from database import get_db
                from datetime import datetime, timezone, timedelta
                if effective_recording:
                    expires_iso = None
                else:
                    expires_iso = (datetime.now(timezone.utc)
                                   + timedelta(hours=24)).isoformat()
                get_db().table("conversations").insert([
                    {"user_id": current_user["sub"], "role": "user",
                     "content": transcript, "expires_at": expires_iso},
                    {"user_id": current_user["sub"], "role": "pixel",
                     "content": reply_text, "expires_at": expires_iso},
                ]).execute()
                _save_extracted_memories(current_user["sub"], extracted_memories)
        except Exception as e:
            print(f"[voice] background persist failed: {e}")

    async def tts_stream():
        # 后台任务：TTS 流刚启动就并行开写库，不阻塞首帧
        persist_task = None
        if current_user:
            persist_task = asyncio.create_task(asyncio.to_thread(_persist_all_sync))
        try:
            communicate = edge_tts.Communicate(reply_text, voice)
            first_chunk = True
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and chunk.get("data"):
                    if first_chunk:
                        ttfb = int((time.perf_counter() - t2) * 1000)
                        print(f"[voice] TTS first audio chunk in {ttfb}ms")
                        first_chunk = False
                    yield chunk["data"]
            if first_chunk:
                print("[voice] TTS produced 0 audio chunks")
        except Exception as e:
            print(f"[voice] TTS stream error: {e}")
        finally:
            # 等后台 DB 写完再退出 generator —— 否则 Vercel 会立刻冻结实例，
            # 写到一半的 task 被吞，对话/记忆就丢了
            if persist_task is not None:
                try:
                    await persist_task
                except Exception as e:
                    print(f"[voice] persist_task await error: {e}")

    # 文字编码成 ASCII-safe header（去掉非 Latin-1 字符用 URL encoding）
    from urllib.parse import quote
    return StreamingResponse(
        tts_stream(),
        media_type="audio/mpeg",
        headers={
            "X-Transcript":   quote(transcript[:200]),
            "X-Reply":        quote(reply_text[:200]),
            "X-Language":     detected_lang or "zh",
            # 后台异步写库 → header 必须在流出前定，所以这两个是「计划值」
            # X-Saved=1 表示我们派发了写入任务（不等于真的写成功，失败看后端 log）
            # X-Memories-Planned 是 Gemini 提取出的候选数量，去重/校验后实际入库可能更少
            "X-Saved":              "1" if current_user else "0",
            "X-Recording":          "1" if effective_recording else "0",
            "X-Recording-Toggle":   toggle or "",
            "X-Translation":        "1" if effective_translation else "0",
            "X-Translation-Pair":   (
                f"{effective_translation_pair[0]}:{effective_translation_pair[1]}"
                if effective_translation and all(effective_translation_pair) else ""
            ),
            "X-Translation-Toggle": translation_toggle or "",
            "X-History-Used":       str(len(history_context)),
            "X-Memories-Used":      str(len(memories_context)),
            "X-Memories-Planned":   str(len(extracted_memories) if isinstance(extracted_memories, list) else 0),
            "X-Soul-Used":          "1" if soul_prompt else "0",
            "X-Voice":        voice,
            # 后端分段计时（毫秒）— 流式化后 tts_ms 不再可在 header 报告，
            # 改为运行时打印（见上方）
            "X-Timing":       json.dumps(timings),
            "X-Streaming":    "1",
            "Content-Disposition": "inline; filename=pixel_reply.mp3",
        },
    )
