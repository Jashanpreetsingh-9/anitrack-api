import asyncio
import time

import httpx

from app.config import settings
from app.errors import UpstreamError

TIMEOUT = httpx.Timeout(10.0)

RETRY_STATUSES = {500, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0

SEARCH_CACHE_TTL = 600  # 10 minutes
SEARCH_CACHE_MAX_SIZE = 256
_search_cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}


def _cache_set(key: tuple[str, int], results: list[dict]) -> None:
    if len(_search_cache) >= SEARCH_CACHE_MAX_SIZE:
        oldest_key = min(_search_cache, key=lambda k: _search_cache[k][0])
        del _search_cache[oldest_key]
    _search_cache[key] = (time.monotonic(), results)


async def _get_from(base_url: str, path: str, params: dict | None = None) -> dict:
    """GET from one upstream with retries on transient failures."""
    last_error = "unknown error"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await client.get(f"{base_url}{path}", params=params)
            except httpx.RequestError as exc:
                last_error = f"{base_url} unreachable: {exc}"
            else:
                if response.status_code < 400:
                    return response.json()

                if response.status_code == 404:
                    raise UpstreamError(f"No record found at {path}")
                if response.status_code == 429:
                    last_error = "Upstream rate limit exceeded"
                elif response.status_code in RETRY_STATUSES:
                    last_error = f"Upstream returned {response.status_code}"
                else:
                    raise UpstreamError(
                        f"Upstream returned {response.status_code}: {response.text[:200]}"
                    )

            if attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(BACKOFF_SECONDS * (2**attempt))

    raise UpstreamError(last_error)


async def _get(path: str, params: dict | None = None) -> dict:
    """Try the primary source; fall back to the secondary if it's unavailable."""
    try:
        return await _get_from(settings.anime_api_base_url, path, params)
    except UpstreamError as primary_error:
        if not settings.anime_api_fallback_url:
            raise
        try:
            return await _get_from(settings.anime_api_fallback_url, path, params)
        except UpstreamError:
            raise primary_error from None


async def fetch_anime(mal_id: int) -> dict:
    payload = await _get(f"/anime/{mal_id}")
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

    _cache_set(key, results)
    return results


async def fetch_top_anime(page: int = 1) -> list[dict]:
    payload = await _get("/top/anime", params={"page": page})
    return payload["data"]


async def fetch_season_now(page: int = 1) -> list[dict]:
    payload = await _get("/seasons/now", params={"page": page})
    return payload["data"]


def to_anime_fields(data: dict) -> dict:
    return {
        "mal_id": data["mal_id"],
        "title": data.get("title_english") or data["title"],
        "synopsis": data.get("synopsis"),
        "image_url": data.get("images", {}).get("jpg", {}).get("large_image_url"),
        "episodes": data.get("episodes"),
        "is_airing": data.get("airing", False),
        "author": None,
        "rating": data.get("rating"),
        "duration": data.get("duration"),
        "type": data.get("type"),
        "trailer_youtube_id": data.get("trailer", {}).get("youtube_id"),
        "trailer_embed_url": data.get("trailer", {}).get("embed_url"),
    }


def extract_genre_names(data: dict) -> list[tuple[str, str]]:
    """Returns (name, category) pairs for genres, themes, and demographics."""
    pairs = []
    for g in data.get("genres", []):
        pairs.append((g["name"], "genre"))
    for t in data.get("themes", []):
        pairs.append((t["name"], "theme"))
    for d in data.get("demographics", []):
        pairs.append((d["name"], "demographic"))
    return pairs


async def fetch_streaming(mal_id: int) -> list[dict]:
    try:
        payload = await _get(f"/anime/{mal_id}/streaming")
    except UpstreamError:
        return []  # no streaming data listed for this title — not a failure
    return payload.get("data", [])
