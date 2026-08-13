Readme · MD

# AniTrack API

Backend for AniTrack v2 — an anime watchlist tracker with LLM-generated
recommendations. Complete rewrite of the v1 Express/Prisma stack.

FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic · Docker

---

## Why this stack

| Choice                 | Reason                                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| FastAPI over Express   | Native async, Pydantic validation at the boundary, better ergonomics for LLM API integration                                 |
| SQLAlchemy over Prisma | Direct control over query construction and eager-loading strategy; drop to Core or raw SQL when the ORM isn't the right tool |
| Alembic                | Versioned, reviewable migrations checked into source control                                                                 |
| Vercel / Render / Neon | Managed deploys with no ops overhead; replaces v1's hand-rolled AWS setup                                                    |

---

## Architecture

Dependencies point in exactly one direction:

```
routes/  →  services/  →  models/   (database)
                       →  clients/  (external APIs)
```

Nothing lower ever imports something higher. If `services/` needs
something from `routes/`, logic is in the wrong layer.

| Path              | Responsibility                                                                                                       |
| ----------------- | -------------------------------------------------------------------------------------------------------------------- |
| `app/config.py`   | Single `Settings` object read from `.env`. Nothing else calls `os.getenv`.                                           |
| `app/db.py`       | Async engine and session factory. Nothing else constructs an engine.                                                 |
| `app/deps.py`     | Request-scoped FastAPI dependencies: `get_session`, `get_current_user`.                                              |
| `app/security.py` | Password hashing and JWT encode/decode. No DB or HTTP imports — pure crypto.                                         |
| `app/errors.py`   | Domain exceptions. Translated to HTTP status codes by handlers in `main.py`.                                         |
| `app/models/`     | SQLAlchemy declarative models. The only source Alembic autogenerate reads.                                           |
| `app/schemas/`    | Pydantic request/response shapes. Deliberately separate from models so DB changes don't silently become API changes. |
| `app/routes/`     | HTTP surface only — path, auth, response model, one service call.                                                    |
| `app/services/`   | Business logic and queries. Raises domain errors, never `HTTPException`.                                             |
| `app/clients/`    | Outbound I/O (Jikan, LLM provider). Knows nothing about the database.                                                |

### Design decisions worth knowing

**Explicit commits.** `get_session` yields a session and closes it; it does
_not_ commit. Each service commits its own writes. This keeps transactions
from staying open across slow third-party HTTP calls (Jikan, the LLM), and
keeps the decision with the code that knows whether the work is complete.

Trade-off: forgetting `await session.commit()` silently discards a write.

**Eager loading is required, not optional.** `WatchlistOut` embeds a nested
`AnimeOut`, so Pydantic walks the relationship during serialization. Under
async SQLAlchemy a lazy load at that point raises `MissingGreenlet` rather
than quietly firing a query — so watchlist queries use
`selectinload(Watchlist.anime)`. Two queries total regardless of list size.

**Ownership is enforced in the WHERE clause.** Every watchlist lookup filters
on `entry_id` AND `user_id` together. There is no code path that loads a row
first and checks ownership afterwards. The user id always comes from the JWT,
never from request input.

**Uniqueness is enforced by Postgres.** Duplicate registration and duplicate
watchlist entries are caught as `IntegrityError` and converted to 409, rather
than pre-checked with a SELECT — a pre-check is a race under concurrency.

**The LLM sits behind a one-function interface.** `clients/llm.py` exposes
`complete(system, user) -> str`. Nothing above it knows the provider. Model
and base URL are config, so switching tiers or vendors doesn't touch the
service layer. LLM output is treated as untrusted input: parsed defensively,
and de-duplicated against the user's watchlist in code rather than trusting
the prompt.

---

## Data model

**`users`** — `email` and `username` both unique; login accepts either.
Passwords stored as bcrypt hashes; `UserOut` has no password field at all,
so a hash cannot leak through a route.

**`anime`** — local catalog. `jikan_id` is unique, which makes ingestion
idempotent. Most metadata fields are nullable because Jikan's data is uneven.

**`watchlist`** — one row per user/anime pair.

- `UniqueConstraint(user_id, anime_id)` — a show can't be added twice
- `CheckConstraint(score BETWEEN 1 AND 10)` — NULL means unrated and passes
  the constraint, since `NULL >= 1` is NULL rather than false
- `status` is a Postgres enum (`watch_status`) storing lowercase values
  Timestamps use `timestamptz` with `server_default=func.now()`, so Postgres
  owns the clock rather than the app process.

> Note: `default=` on `episodes_watched`, `status`, and `is_active` is applied
> by SQLAlchemy in Python, not by Postgres. Inserts made outside the ORM
> (seed scripts, data migrations, psql) will not get those defaults.

---

## Setup

**Requirements:** Python 3.14, [uv](https://docs.astral.sh/uv/), Docker.

```bash
uv sync
cp .env.example .env          # then fill in the values below
docker compose up -d          # Postgres on host port 5433
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Interactive docs at http://localhost:8000/docs — use the **Authorize**
button to log in and exercise protected endpoints.

### Environment

| Variable                      | Notes                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `DATABASE_URL`                | Must use the `postgresql+asyncpg://` scheme, not `postgresql://`             |
| `SECRET_KEY`                  | Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional, defaults to 7 days                                                 |
| `DEEPSEEK_API_KEY`            | Recommendations return an error without it                                   |
| `LLM_BASE_URL` / `LLM_MODEL`  | Optional; override to switch model tier or provider                          |
| `CORS_ORIGINS`                | Comma-separated. Must include the frontend origin or browser requests fail   |

Postgres is mapped to host port **5433**, not 5432, because AniTrack v1's
container still holds the default port locally.

---

## API

All watchlist and recommendation endpoints require
`Authorization: Bearer <token>`.

### Auth

| Method | Path             | Description                                                                |
| ------ | ---------------- | -------------------------------------------------------------------------- |
| `POST` | `/auth/register` | Create an account. 409 if username or email is taken.                      |
| `POST` | `/auth/login`    | Form-encoded. `username` field accepts username _or_ email. Returns a JWT. |
| `GET`  | `/auth/me`       | Current user.                                                              |

### Anime

| Method | Path                | Description                                                             |
| ------ | ------------------- | ----------------------------------------------------------------------- |
| `GET`  | `/anime/search?q=`  | Proxies Jikan search. Results are not persisted.                        |
| `GET`  | `/anime/{anime_id}` | Local catalog record.                                                   |
| `POST` | `/anime`            | Import by `jikan_id`. Idempotent — returns the existing row if present. |

`/anime/search` is registered **before** `/anime/{anime_id}`. FastAPI matches
in registration order, so reversing them would make `search` parse as an int
and 422.

### Watchlist

| Method   | Path                    | Description                                       |
| -------- | ----------------------- | ------------------------------------------------- |
| `GET`    | `/watchlist`            | Caller's entries with nested anime, newest first. |
| `POST`   | `/watchlist`            | Add an entry. 409 if already present.             |
| `PATCH`  | `/watchlist/{entry_id}` | Partial update — omitted fields are untouched.    |
| `DELETE` | `/watchlist/{entry_id}` | 204 on success.                                   |

### Recommendations

| Method | Path               | Description                                                                  |
| ------ | ------------------ | ---------------------------------------------------------------------------- |
| `GET`  | `/recommendations` | LLM suggestions from the caller's watchlist. `[]` if the watchlist is empty. |

### Error responses

| Status | Raised by          | Meaning                                                  |
| ------ | ------------------ | -------------------------------------------------------- |
| 401    | `get_current_user` | Missing, expired, or invalid token                       |
| 404    | `NotFoundError`    | Resource absent, or not owned by the caller              |
| 409    | `ConflictError`    | Uniqueness violation                                     |
| 422    | FastAPI            | Request failed schema validation                         |
| 502    | `UpstreamError`    | Jikan or the LLM provider failed — not an AniTrack fault |

---

## Migrations

```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

`alembic/env.py` imports every model explicitly (marked `# noqa: F401`) —
`Base.metadata` is populated as a side effect of class definition, so without
those imports autogenerate produces an empty migration with no error. The DB
URL is injected from `Settings`, so `alembic.ini` holds no credentials.

**Always read generated migrations before applying them.** Two known gaps:

- Autogenerate does not detect changes to enum _values_. Adding a status
  requires a hand-written `ALTER TYPE ... ADD VALUE`.
- It does not emit `DROP TYPE` for enums on downgrade. The initial migration
  has this added by hand; future ones need the same.

---

## Known gaps

- `anime.author` is always NULL. Jikan's `/anime/{id}` has no author field —
  populating it needs `/anime/{id}/full` to find the source manga relation,
  then `/manga/{id}`. Three requests against a 3/sec limit, so it belongs on
  the detail page rather than bulk ingestion.
- No tests yet. `pytest`, `pytest-asyncio`, and `httpx` are installed.
- No Dockerfile yet — planned as multi-stage, base image pinned to match
  `.python-version`.
- `echo=True` is on the engine. Turn it off (or drive it from settings)
  before deploying.
- Neon's pooled endpoint runs PgBouncer in transaction mode, which conflicts
  with asyncpg's per-connection prepared-statement cache. Needs connect-args
  configuration before the first deploy; it will not reproduce locally.
