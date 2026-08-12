import httpx

from app.errors import UpstreamError

BASE_URL = "https://api.jikan.moe/v4"
TIMEOUT = httpx.Timeout(10.0)


async def fetch_anime(jikan_id: int) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{BASE_URL}/anime/{jikan_id}")
        except httpx.RequestError as exc:
            raise UpstreamError(f"Jikan unreachable: {exc}") from exc

    if response.status_code == 404:
        raise UpstreamError(f"Jikan has no anime with id {jikan_id}")
    if response.status_code == 429:
        raise UpstreamError("Jikan rate limit exceeded")
    if response.status_code >= 400:
        raise UpstreamError(f"Jikan returned {response.status_code}")

    payload = response.json()
    return payload["data"]


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