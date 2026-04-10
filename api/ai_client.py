"""
Pixel AI 挂件 — AI 引擎统一接口（httpx 直接请求版）
引擎优先级：gemma（Google AI Studio）> ollama > grok > claude
"""

from config import (
    AI_ENGINE,
    GOOGLE_API_KEY, GOOGLE_BASE_URL, GEMMA_MODEL,
    XAI_API_KEY, XAI_BASE_URL, GROK_MODEL,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
)


async def chat_completion(system_prompt: str, user_message: str, max_tokens: int = 512) -> str:
    """统一的 AI 对话接口，根据 AI_ENGINE 配置自动选择引擎。"""
    if AI_ENGINE == "gemma":
        return await _openai_compat_chat(GOOGLE_API_KEY, GOOGLE_BASE_URL, GEMMA_MODEL, system_prompt, user_message, max_tokens)
    elif AI_ENGINE == "ollama":
        return await _openai_compat_chat("ollama", OLLAMA_BASE_URL, OLLAMA_MODEL, system_prompt, user_message, max_tokens)
    elif AI_ENGINE == "grok":
        return await _openai_compat_chat(XAI_API_KEY, XAI_BASE_URL, GROK_MODEL, system_prompt, user_message, max_tokens)
    else:
        return await _claude_chat(system_prompt, user_message, max_tokens)


async def _openai_compat_chat(api_key: str, base_url: str, model: str, system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 httpx 直接调用 OpenAI 兼容接口。"""
    import httpx

    # 确保 base_url 末尾有斜杠
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    url = base_url + "chat/completions"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=55.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _claude_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 Anthropic Claude API（httpx 直接调用）。"""
    import httpx

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=55.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


def get_engine_name() -> str:
    """返回当前使用的引擎名称。"""
    if AI_ENGINE == "gemma":
        return f"Gemma ({GEMMA_MODEL})"
    elif AI_ENGINE == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    elif AI_ENGINE == "grok":
        return f"Grok ({GROK_MODEL})"
    return f"Claude ({CLAUDE_MODEL})"
