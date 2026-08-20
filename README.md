# AniTrack API

Backend for AniTrack v2 — an anime watchlist tracker with LLM-generated
recommendations. Complete rewrite of the v1 Express/Prisma stack.

FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic · Docker

Live: `https://anitrack-api.onrender.com` — interactive docs at `/docs`.

---

## Why this stack

| Choice                 | Reason                                                                                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FastAPI over Express   | Native async, Pydantic validation at the boundary, better ergonomics for LLM API integration                                                                 |
| SQLAlchemy over Prisma | Direct control over query construction and eager-loading strategy; drop to Core or raw SQL when the ORM isn't the right tool                                 |
| Alembic                | Versioned, reviewable migrations checked into source control                                                                                                 |
| Render / Neon          | Managed deploys with no ops overhead; replaces v1's hand-rolled AWS setup                                                                                    |
| Tenrai over Jikan      | Tenrai serves its own MyAnimeList mirror rather than proxying live, so it survives upstream outages. Jikan-compatible schema, plus correct pagination totals |

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
| `app/clients/`    | Outbound I/O (anime metadata, LLM provider). Knows nothing about the database.                                       |

### Design decisions worth knowing

**Explicit commits.** `get_session` yields a session and closes it; it does
_not_ commit. Each service commits its own writes. This keeps transactions
from staying open across slow third-party HTTP calls (anime API, the LLM),
and keeps the decision with the code that knows whether the work is complete.

Trade-off: forgetting `await session.commit()` silently discards a write.

**Eager loading is required, not optional.** `WatchlistOut` embeds a nested
`AnimeOut`, so Pydantic walks the relationship during serialization. Under
async SQLAlchemy a lazy load at that point raises `MissingGreenlet` rather
than quietly firing a query — so watchlist queries use
`selectinload(Watchlist.anime)`. Two queries total regardless of list size.

**Ownership is enforced in the WHERE clause.** Every watchlist lookup filters
on `entry_id` AND `user_id` together. There is no code path that loads a row
first and checks ownership afterwards. The user id always comes from the JWT,
never from request input. Two tests pin this.

**Uniqueness is enforced by Postgres.** Duplicate registration and duplicate
watchlist entries are caught as `IntegrityError` and converted to 409, rather
than pre-checked with a SELECT — a pre-check is a race under concurrency.

**The anime source has a primary and a fallback.** `clients/anime_source.py`
exposes `_get_from(base_url, path)` with retry, and `_get(path)` which tries
Tenrai then falls back to Jikan. Retries cover 5xx, 429, and network errors
with exponential backoff; 4xx raises immediately, since retrying a 400 just
triples latency before failing anyway. Both upstreams speak the same schema,
so `to_anime_fields` is shared and the vendor choice is a config value.

Search responses are cached in-process for 10 minutes, keyed on normalized
query and limit. **Only successful responses are cached** — caching a failure
would poison that query for the whole TTL.

**The LLM sits behind a one-function interface.** `clients/llm.py` exposes
`complete(system, user) -> str`. Nothing above it knows the provider. Model
and base URL are config, so switching tiers or vendors doesn't touch the
service layer. LLM output is treated as untrusted input: parsed defensively,
and de-duplicated against the user's watchlist in code rather than trusting
the prompt to honour that instruction.

---

## Data model

**`users`** — `email` and `username` both unique; login accepts either.
Passwords stored as bcrypt hashes; `UserOut` has no password field at all,
so a hash cannot leak through a route.

**`anime`** — local catalog. `jikan_id` holds the MyAnimeList ID and is
unique, which makes ingestion idempotent. Most metadata fields are nullable
because upstream data is uneven — not-yet-aired entries have null episodes,
score, and images.

**`watchlist`** — one row per user/anime pair.

- `UniqueConstraint(user_id, anime_id)` — a show can't be added twice
- `CheckConstraint(score BETWEEN 1 AND 10)` — NULL means unrated and passes
  the constraint, since `NULL >= 1` is NULL rather than false
- `status` is a Postgres enum (`watch_status`) storing lowercase values via
  `values_callable`; without it SQLAlchemy persists the member _names_

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
uv run python -m alembic upgrade head
uv run uvicorn app.main:app --reload
```

Interactive docs at http://localhost:8000/docs — use the **Authorize**
button to log in and exercise protected endpoints.

Commands use `python -m` rather than the console scripts: Windows Smart App
Control blocks the unsigned shims uv generates in `.venv/Scripts`.

### Catalog sync (Tenrai → Neon)

Explore reads **only Neon**. Tenrai is not queried on page load. To fill or
refresh the catalog (top-rated + currently airing), run:

```bash
uv run python scripts/seed.py
```

That upserts by `mal_id`, so re-running updates scores, rank, and `is_airing`.
It is slow on purpose (rate-limit delay + a streaming lookup per title).

Production refresh is a daily GitHub Action (`.github/workflows/sync-catalog.yml`)
plus **Actions → Sync catalog → Run workflow**. Add these repository secrets:

- `DATABASE_URL` — same Neon URL the API uses (`postgresql+asyncpg://…`)
- `SECRET_KEY` and `INTERNAL_AUTH_SECRET` — required to boot app settings

Do **not** fetch Tenrai from the explore page. That would make `/explore`
slow, flaky, and coupled to Tenrai uptime.

### Environment

| Variable                      | Notes                                                                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                | Required. Must use the `postgresql+asyncpg://` scheme, and no `sslmode` / `channel_binding` query params — asyncpg rejects both |
| `SECRET_KEY`                  | Required. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`                                          |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional, defaults to 7 days                                                                                                    |
| `DEEPSEEK_API_KEY`            | Recommendations return 502 without it; the rest of the app runs fine                                                            |
| `LLM_BASE_URL` / `LLM_MODEL`  | Optional; override to switch model tier or provider                                                                             |
| `ANIME_API_BASE_URL`          | Optional; defaults to Tenrai                                                                                                    |
| `ANIME_API_FALLBACK_URL`      | Optional; defaults to Jikan. Set empty to disable fallback                                                                      |
| `CORS_ORIGINS`                | Comma-separated. Must include the frontend origin or browser requests fail                                                      |
| `DB_ECHO`                     | Optional; `true` logs all SQL. Leave unset in production — it logs parameter values                                             |

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

| Method | Path                | Description                                                                 |
| ------ | ------------------- | --------------------------------------------------------------------------- |
| `GET`  | `/anime/search?q=`  | Proxies the upstream anime API. Results are not persisted.                  |
| `GET`  | `/anime/{anime_id}` | Local catalog record.                                                       |
| `POST` | `/anime`            | Import by MyAnimeList ID. Idempotent — returns the existing row if present. |

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

| Status | Raised by          | Meaning                                                      |
| ------ | ------------------ | ------------------------------------------------------------ |
| 401    | `get_current_user` | Missing, expired, or invalid token                           |
| 404    | `NotFoundError`    | Resource absent, or not owned by the caller                  |
| 409    | `ConflictError`    | Uniqueness violation                                         |
| 422    | FastAPI            | Request failed schema validation                             |
| 502    | `UpstreamError`    | The anime API or LLM provider failed — not an AniTrack fault |

---

## Tests

```bash
uv run pytest -q
```

Tests run against a real Postgres (`anitrack_test`), created automatically by
`conftest.py` if it doesn't exist. Not SQLite — the schema uses a Postgres
enum, `timestamptz`, and a check constraint that SQLite would treat
differently.

**Isolation.** The `session` fixture opens a transaction and binds an
`AsyncSession` with `join_transaction_mode="create_savepoint"`. Service code
calls `commit()` exactly as it does in production, but the commit releases a
savepoint inside the fixture's outer transaction, which is rolled back after
each test. No changes to the code under test, no cross-test pollution.

The engine uses `NullPool` and pytest-asyncio is pinned to a session-scoped
loop. Without both, connections get reused across event loops and asyncpg
fails with `another operation is in progress`.

`client` overrides the `get_session` dependency so route tests share the
transaction. `auth_client` registers and logs in a user, then attaches the
bearer token.

Schema comes from `Base.metadata.create_all`, not Alembic — faster, and CI
proves the migrations separately.

---

## Migrations

```bash
uv run python -m alembic revision --autogenerate -m "description"
uv run python -m alembic upgrade head
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

Run migrations against Neon's **direct** endpoint, not the pooled one — DDL
in a transaction doesn't survive PgBouncer's transaction-mode pooling.

---

## CI/CD

`.github/workflows/ci.yml` runs on every push and pull request:

| Job      | What it catches                                                                                                                              |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `lint`   | `ruff check` and `ruff format --check` — fails on unformatted code rather than rewriting it                                                  |
| `test`   | Migrations applied to an empty database, `alembic check` for model/migration drift, then the suite against a real Postgres service container |
| `docker` | A Dockerfile that builds locally but not in a clean context                                                                                  |
| `deploy` | `needs: [lint, test, docker]`, main only — curls Render's deploy hook                                                                        |

`alembic check` is the one that earns its slot: it fails when models have
changed without a corresponding migration, which is otherwise a bug you find
at deploy time.

Render's auto-deploy is **off**; the `deploy` job is the only path to
production, so a red build cannot ship.

---

## Deployment

Frontend on Vercel, API on Render, database on Neon (`us-west-2`, colocated
with Render's Oregon region).

**Render** builds from the Dockerfile — multi-stage, dependencies installed
before app code so a route edit doesn't reinstall the dependency tree.
`--host 0.0.0.0` and `${PORT}` are both required or health checks time out
with no useful error. Health Check Path is `/health`, which queries the
database, so Render won't route traffic to an instance that can't reach Neon.

**Neon connection.** The app uses the **pooled** endpoint with
`statement_cache_size=0` and `prepared_statement_cache_size=0` in
`connect_args`. asyncpg names and caches prepared statements per connection;
PgBouncer in transaction mode hands out a different backend connection each
transaction, so the cached name isn't there. The symptom is intermittent
`InvalidSQLStatementNameError` under concurrency, in production only.
`pool_pre_ping=True` covers Neon dropping idle connections.

**Cold starts.** Render's free tier spins down after ~15 minutes idle; the
first request after that takes 30–60s. Neon suspends after 5 minutes and adds
0.5–2s. The frontend needs real loading states, or a keep-warm ping.

---

## Known gaps

- `anime.author` is always NULL. The `/anime/{id}` endpoint has no author
  field — populating it needs the source manga relation, then a second call
  to `/manga/{id}`. Two extra requests per title against a rate-limited API,
  so it belongs on the detail page rather than bulk ingestion.
- The `jikan_id` column is really a MyAnimeList ID, and is now misleading
  given Jikan is the fallback rather than the primary. Rename pending.
- The search cache is a per-process dict: it dies on restart, isn't shared
  across instances, and grows unbounded. Fine at current scale; Redis and an
  LRU bound are the answer if it stops being fine.
- No explore page data. Score, rank, popularity, season, and genres all come
  back in the search payload already but aren't persisted — that needs new
  columns, a genres many-to-many, and an upsert path so a re-sync refreshes
  rows instead of skipping them.
- Search proxies upstream on every miss. Seeding a local catalog would make
  most queries never leave the database.
