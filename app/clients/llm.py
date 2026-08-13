import json

import httpx

from app.config import settings
from app.errors import UpstreamError

TIMEOUT = httpx.Timeout(60.0)


async def complete(system: str, user: str) -> str:
    """Send a prompt to the configured LLM provider, return the text response."""
    if not settings.deepseek_api_key:
        raise UpstreamError("LLM provider is not configured")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
        except httpx.RequestError as exc:
            raise UpstreamError(f"LLM provider unreachable: {exc}") from exc

    if response.status_code == 429:
        raise UpstreamError("LLM rate limit exceeded")
    if response.status_code >= 400:
        raise UpstreamError(f"LLM provider returned {response.status_code}")

    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def parse_json_response(text: str) -> list | dict:
    """LLMs wrap JSON in code fences despite instructions. Strip and parse."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError as exc:
        raise UpstreamError("LLM returned malformed JSON") from exc
