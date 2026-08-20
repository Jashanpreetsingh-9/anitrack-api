from app.clients.llm import complete, parse_json_response
from app.errors import UpstreamError
from app.models.user import User
from app.schemas.recommendations import RecommendationItem
from app.services.watchlist import list_entries

SYSTEM_PROMPT = """You are an anime recommendation engine.
Given a user's watchlist, suggest anime they are likely to enjoy.
Respond with ONLY a JSON array, no prose and no code fences.
Each element must have exactly these keys:
  "title": the anime's English or romaji title
  "reason": one sentence, under 25 words, on why it fits this user
Return at most 5 items. Do not recommend anything already on their list."""


async def generate_for_user(session, user: User, limit: int = 5) -> list[dict]:
    entries = await list_entries(session, user.id)
    if not entries:
        return []

    lines = []
    for entry in entries:
        score = f", rated {entry.score}/10" if entry.score else ""
        lines.append(f"- {entry.anime.title} ({entry.status.value}{score})")

    user_prompt = "Watchlist:\n" + "\n".join(lines) + f"\n\nSuggest up to {limit} anime."

    raw = await complete(SYSTEM_PROMPT, user_prompt)
    parsed = parse_json_response(raw)

    if not isinstance(parsed, list):
        raise UpstreamError("LLM returned an unexpected shape")

    seen = {entry.anime.title.lower() for entry in entries}
    results: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            rec = RecommendationItem.model_validate(item)
        except Exception:
            continue
        if rec.title.lower() in seen:
            continue
        results.append(rec.model_dump())
        if len(results) >= limit:
            break
    return results
