import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.clients.anime_source import fetch_season_now, fetch_top_anime  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.anime import upsert_anime  # noqa: E402

PAGES_TO_SEED = 5
RATE_LIMIT_DELAY = 2.0


async def seed_top_anime():
    async with SessionLocal() as session:
        for page in range(1, PAGES_TO_SEED + 1):
            raw_list = await fetch_top_anime(page=page)
            for raw in raw_list:
                await upsert_anime(session, raw)
            print(f"Seeded top/anime page {page} ({len(raw_list)} titles)")
            await asyncio.sleep(RATE_LIMIT_DELAY)


async def seed_current_season():
    async with SessionLocal() as session:
        page = 1
        while True:
            raw_list = await fetch_season_now(page=page)
            if not raw_list:
                break
            for raw in raw_list:
                await upsert_anime(session, raw)
            print(f"Seeded seasons/now page {page} ({len(raw_list)} titles)")
            page += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)


async def main():
    await seed_top_anime()
    await seed_current_season()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
