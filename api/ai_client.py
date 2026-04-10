"""
Pixel AI 挂件 — AI 引擎统一接口（异步版）
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
        return await _gemma_chat(system_prompt, user_message, max_tokens)
    elif AI_ENGINE == "ollama":
        return await _ollama_chat(system_prompt, user_message, max_tokens)
    elif AI_ENGINE == "grok":
        return await _grok_chat(system_prompt, user_message, max_tokens)
    else:
        return await _claude_chat(system_prompt, user_message, max_tokens)


async def _gemma_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 Google AI Studio Gemma（OpenAI 兼容格式，异步）。"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=GOOGLE_API_KEY, base_url=GOOGLE_BASE_URL, max_retries=0)

    response = await client.chat.completions.create(
        model=GEMMA_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content


async def _grok_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 xAI Grok API（OpenAI 兼容格式，异步）。"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL, max_retries=0)

    response = await client.chat.completions.create(
        model=GROK_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content


async def _claude_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 Anthropic Claude API（异步）。"""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


async def _ollama_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 Ollama（OpenAI 兼容格式，异步），支持本地和远程实例。"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL, max_retries=0)

    response = await client.chat.completions.create(
        model=OLLAMA_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content


def get_engine_name() -> str:
    """返回当前使用的引擎名称。"""
    if AI_ENGINE == "gemma":
        return f"Gemma ({GEMMA_MODEL})"
    elif AI_ENGINE == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    elif AI_ENGINE == "grok":
        return f"Grok ({GROK_MODEL})"
    return f"Claude ({CLAUDE_MODEL})"
