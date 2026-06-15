"""Groq LLM client — thin wrapper around the official groq SDK."""
from groq import Groq
from config import get_settings

settings = get_settings()

_client: Groq | None = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """
    Send a chat completion request and return the assistant message text.

    Args:
        messages: List of {"role": "...", "content": "..."} dicts.
        model: Groq model ID. Defaults to settings.groq_model.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        The assistant's reply as a plain string.
    """
    client = get_groq_client()
    response = client.chat.completions.create(
        model=model or settings.groq_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
