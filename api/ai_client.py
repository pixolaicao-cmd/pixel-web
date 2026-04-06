"""
Pixel AI 挂件 — AI 引擎统一接口
支持 Grok (xAI) 和 Claude (Anthropic) 双引擎，接口一致。
"""

from config import (
    AI_ENGINE, XAI_API_KEY, XAI_BASE_URL, GROK_MODEL,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
)


def chat_completion(system_prompt: str, user_message: str, max_tokens: int = 512) -> str:
    """统一的 AI 对话接口，根据 AI_ENGINE 配置自动选择引擎。"""
    if AI_ENGINE == "ollama":
        return _ollama_chat(system_prompt, user_message, max_tokens)
    elif AI_ENGINE == "grok":
        return _grok_chat(system_prompt, user_message, max_tokens)
    else:
        return _claude_chat(system_prompt, user_message, max_tokens)


def _grok_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 xAI Grok API（OpenAI 兼容格式）。"""
    from openai import OpenAI

    client = OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL)

    response = client.chat.completions.create(
        model=GROK_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content


def _claude_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 Anthropic Claude API。"""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


def _ollama_chat(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """通过 Ollama（OpenAI 兼容格式），支持本地和远程实例。"""
    from openai import OpenAI

    client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)

    response = client.chat.completions.create(
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
    if AI_ENGINE == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    elif AI_ENGINE == "grok":
        return f"Grok ({GROK_MODEL})"
    return f"Claude ({CLAUDE_MODEL})"
