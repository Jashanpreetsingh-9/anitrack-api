import asyncio
import time

import httpx

from app.errors import UpstreamError

BASE_URL = "https://api.jikan.moe/v4"
TIMEOUT = httpx.Timeout(10.0)

RETRY_STATUSES = {500, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0

SEARCH_CACHE_TTL = 600  # 10 minutes
_search_cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}


async def _get(path: str, params: dict | None = None) -> dict:
    """GET from Jikan with retries on transient upstream failures."""
    last_error = "unknown error"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await client.get(f"{BASE_URL}{path}", params=params)
            except httpx.RequestError as exc:
                last_error = f"Jikan unreachable: {exc}"
            else:
                if response.status_code < 400:
                    return response.json()

                if response.status_code == 404:
                    raise UpstreamError(f"Jikan has no record at {path}")
                if response.status_code == 429:
                    last_error = "Jikan rate limit exceeded"
                elif response.status_code in RETRY_STATUSES:
                    last_error = f"Jikan returned {response.status_code}"
                else:
                    raise UpstreamError(
                        f"Jikan returned {response.status_code}: {response.text[:200]}"
                    )

            if attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(BACKOFF_SECONDS * (2**attempt))

    raise UpstreamError(last_error)


async def fetch_anime(jikan_id: int) -> dict:
    payload = await _get(f"/anime/{jikan_id}")
    return payload["data"]


async def search_anime(query: str, limit: int = 20) -> list[dict]:
    key = (query.strip().lower(), limit)

    cached = _search_cache.get(key)
    if cached is not None:
        cached_at, results = cached
        if time.monotonic() - cached_at < SEARCH_CACHE_TTL:
            return results
        del _search_cache[key]

    payload = await _get("/anime", params={"q": query, "limit": limit})
    results = payload["data"]

    _search_cache[key] = (time.monotonic(), results)
    return results


def to_anime_fields(data: dict) -> dict:
    return {
        "jikan_id": data["mal_id"],
        "title": data.get("title_english") or data["title"],
        "synopsis": data.get("synopsis"),
        "image_url": data.get("images", {}).get("jpg", {}).get("large_image_url"),
        "episodes": data.get("episodes"),
        "is_airing": data.get("airing", False),
        "author": None,
    }
