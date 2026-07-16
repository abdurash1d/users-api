# Users API

[![CI](https://github.com/abdurash1d/users-api/actions/workflows/ci.yml/badge.svg)](https://github.com/abdurash1d/users-api/actions/workflows/ci.yml)

A user management module built as an extensible modular monolith on FastAPI:
registration, JWT authentication, email verification, roles (user/admin), and
automatic cleanup of unverified accounts. It exposes a clean HTTP API with
Swagger docs and runs as a self-contained Docker Compose stack (API, Postgres,
Redis, and a Celery worker/beat pair for background cleanup).

## Tech stack

- Python 3.12, FastAPI
- SQLAlchemy 2.0 (async, asyncpg driver), PostgreSQL, Alembic migrations
- Celery + Redis (scheduled background jobs)
- PyJWT (access/refresh tokens), pwdlib with argon2 (password hashing)
- Docker Compose, pytest, ruff, uv (dependency management)

## Quickstart (Docker)

```bash
cp .env.example .env
```

Set `USERS_API_JWT_SECRET_KEY` in `.env` to a random value of at least 32
characters. The application intentionally has no default signing key and
refuses to start when the key is missing or too short. Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

If ports `8000` or `5433` are already taken on your machine, override
`API_PORT` / `DB_PORT` in `.env`. Application settings use the
`USERS_API_` prefix so unrelated host variables such as `DEBUG` cannot alter
the service configuration.

```bash
docker compose up -d --build
```

This starts the API, Postgres, Redis, a Celery worker, and Celery beat.
Alembic migrations run automatically on API startup.

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Create the first admin user:

```bash
docker compose exec api python -m scripts.create_admin admin@example.com StrongPass123
```

Signup verification codes are not emailed in this setup — they are printed to
the API container log:

```bash
docker compose logs api
```

## Try the flow

```bash
# 1. Sign up
curl -s -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "password": "StrongPass123"}'

# 2. Grab the verification code from the logs
docker compose logs api | grep "jane@example.com"

# 3. Verify (replace 123456 with the code from the logs)
curl -s -X POST http://localhost:8000/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "code": "123456"}'

# 4. Log in
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "password": "StrongPass123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 5. Fetch your own profile
curl -s http://localhost:8000/me -H "Authorization: Bearer $TOKEN"
```

## Local development (without Docker for the app)

```bash
uv sync
docker compose up -d db redis
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Tests use a separate database, created once:

```bash
docker compose exec db psql -U postgres -c 'CREATE DATABASE users_test'
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

## Architecture

The project is a modular monolith: shared infrastructure lives in `app/core/`,
and each business domain is a self-contained module under `app/modules/` with
its own router, service (business logic), repository (data access), models,
and schemas. Domain errors are plain Python exceptions (`app/core/exceptions.py`)
that a single FastAPI exception handler in `app/main.py` maps to HTTP
responses, keeping services free of HTTP concerns. Adding a new domain (e.g.
`app/modules/billing/`) means creating one new module folder with the same
router/service/repository shape and including its router in `app/main.py` —
existing modules are untouched.

```
app/
  core/            # config, database, security, exceptions, email, celery
    config.py      # pydantic-settings, env-driven
    database.py    # async engine/session, declarative Base
    security.py    # password hashing, JWT issuance/verification
    exceptions.py  # domain errors -> HTTP status/detail mapping
    email.py       # EmailSender protocol (console impl for dev)
    celery_app.py  # Celery app + beat schedule
  modules/
    auth/          # signup, verify, login, refresh
      router.py service.py schemas.py dependencies.py
    users/         # profile, admin listing, update, delete
      router.py service.py repository.py models.py schemas.py
  tasks.py         # cleanup logic + Celery beat entrypoint
scripts/
  create_admin.py  # bootstraps/promotes an admin user
alembic/           # schema migrations
tests/
```

**Auth scheme.** JWTs carry a `type` claim (`access` or `refresh`) so a
refresh token can never be used where an access token is expected, and vice
versa. Access tokens live 15 minutes; refresh tokens live 7 days. Requests
authenticate via a Bearer token on `/me` and the `/users` endpoints. Login is
only permitted for verified accounts, and unknown-email and wrong-password
attempts return the identical `401` with a timing-equalized check (a dummy
password hash is verified even when the email doesn't exist), so login cannot
be used to enumerate registered accounts.

## Endpoints

| Method | Path            | Access             | Description                                    |
|--------|-----------------|--------------------|-------------------------------------------------|
| POST   | `/auth/signup`  | public             | Register a new (unverified) user                |
| POST   | `/auth/verify`  | public             | Confirm the 6-digit code, mark email verified   |
| POST   | `/auth/login`   | public             | Exchange credentials for an access/refresh pair |
| POST   | `/auth/refresh` | public             | Exchange a refresh token for a new access token |
| GET    | `/me`           | authenticated      | Return the current user's profile               |
| GET    | `/users`        | admin              | List users (paginated)                          |
| GET    | `/users/{id}`   | admin              | Get a single user by ID                         |
| PATCH  | `/users/{id}`   | self or admin      | Update a profile; `role`/`is_verified` are admin-only |
| DELETE | `/users/{id}`   | admin              | Delete a user                                   |
| GET    | `/health`       | public             | Liveness probe                                  |

## Verification flow

Signup generates a random 6-digit numeric code with a 15-minute TTL. Only its
hash is stored on the user row; the plaintext code is handed to a pluggable
`EmailSender` (in this setup, a console/log implementation — see
"Deliberate simplifications" below). `POST /auth/verify` checks the code
against the stored hash with a constant-time comparison and, on success, marks
the user verified and clears the stored code.

## Automatic cleanup

Users who never verify their email are removed automatically. Celery beat
triggers `app.tasks.delete_expired_unverified_users` once an hour; it deletes
any unverified user whose account is older than the configured TTL (2 days by
default). The core deletion logic lives in `purge_unverified_users`, a plain
async function that takes a session and is unit-tested directly, without
needing a running broker. The `worker` and `beat` services in
`docker-compose.yml` run the schedule and execute the task respectively.

## Deliberate simplifications

Each item below is marked `SIMPLIFICATION` (or documented as an accepted
trade-off) in the code, with what a production version would do instead:

- **Stateless refresh tokens** (`app/core/security.py`) — refresh tokens are
  plain JWTs with no server-side record. With more time: persist a `jti` per
  token family so tokens can be rotated and revoked server-side.
- **SHA-256 verification code hashing** (`app/core/security.py`) — codes are
  hashed with unsalted SHA-256, acceptable for a short-lived 6-digit code.
  With more time: salted hashes plus a per-user attempt counter to throttle
  brute-forcing the 1-in-a-million code space.
- **Synchronous email send after commit** (`app/modules/auth/service.py`) —
  the verification code is sent inline in the request after the DB commit,
  with delivery failures caught and logged (never failing signup). With more
  time: dispatch through a Celery queue with retries and an outbox table for
  atomicity with the commit.
- **Plain `String` email column, code on the user row**
  (`app/modules/users/models.py`) — email uniqueness relies on
  case-normalization in the service layer rather than a case-insensitive
  column type, and the verification code lives directly on the user row. With
  more time: PostgreSQL `citext` for email, and a separate
  `verification_codes` table with its own attempt/expiry tracking.
- **Per-run Celery engine** (`app/tasks.py`) — the cleanup task creates and
  disposes a fresh async engine on every invocation, since `asyncio.run()`
  opens a new event loop each time and pooled asyncpg connections can't cross
  loops. With more time: set up one persistent engine per worker process via
  Celery's `worker_process_init` signal instead of paying setup/teardown cost
  every hour.
- **Console-only email delivery** (`app/core/email.py`) — verification codes
  are printed to the application log via the `EmailSender` protocol's dev
  implementation. With more time: add a real SMTP/provider implementation
  selected by settings, with retries.
- **Signup returns 409 on a duplicate email** (`app/modules/auth/service.py`)
  — this is an accepted trade-off, not a bug: it reveals whether an email is
  already registered, which is normally an enumeration risk. It's kept
  because the spec calls for explicit uniqueness feedback at signup; the
  login endpoint stays enumeration-safe (identical error, timing-equalized)
  since that is the higher-value target for an attacker.
