# Users API — Design Spec

**Date:** 2026-07-15
**Source:** Test task "ТЗ Python (FastAPI) для ORB IT" (approved via brainstorming)

## Goal

A production-ready, extensible **modular monolith** Users API on FastAPI: registration,
JWT auth (access + refresh), email verification, automatic cleanup of unverified users,
User/Admin roles, and user-management endpoints. Delivered in a public GitHub repo with
Docker packaging, Swagger docs, focused integration tests, and an English README.

## Approved decisions

| Decision | Choice |
|---|---|
| Cleanup mechanism | Celery worker + beat, Redis broker (hourly task) |
| Database | PostgreSQL (asyncpg), Alembic migrations |
| Verification | 6-digit code, TTL 15 min, stored hashed; dev delivery = console via pluggable `EmailSender` |
| PATCH /users/{id} | Self + Admin: user edits own name/password; admin edits anyone incl. `role`, `is_verified` |
| Tests | Focused pytest integration tests (~15–25) over critical flows |
| Architecture | Domain-module monolith: `app/core/` (cross-cutting) + `app/modules/{auth,users}/` |
| Login policy | Unverified users cannot log in (403 "Email not verified") |
| Refresh tokens | Stateless JWT with `type` claim (simplification: prod would persist jti for rotation/revocation) |

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, Pydantic v2 +
pydantic-settings, PyJWT, pwdlib[argon2], Celery[redis], pytest + pytest-asyncio + httpx,
uv, ruff.

## Endpoints

| Method & path | Access | Purpose |
|---|---|---|
| POST /auth/signup | public | Register; returns user; sends verification code; status unverified |
| POST /auth/verify | public | email + 6-digit code → mark verified |
| POST /auth/login | public (verified only) | email + password → access + refresh tokens |
| POST /auth/refresh | public | refresh token → new access token |
| GET /me | any authenticated | Current user |
| GET /users | admin | List users (limit/offset) |
| GET /users/{id} | admin | Get user by id |
| PATCH /users/{id} | self or admin | Partial update; `role`/`is_verified` admin-only |
| DELETE /users/{id} | admin | Delete user |

## Data model — `users` table

`id UUID pk`, `email str(320) unique lowercased` (simplification: citext in real prod),
`hashed_password`, `first_name?`, `last_name?`, `role enum(user|admin) default user`,
`is_verified bool default false`, `verification_code_hash str(64)?`,
`verification_code_expires_at timestamptz?`, `created_at`, `updated_at`.

## Auth

- Access JWT: 15 min, claims `sub` (user id), `role`, `type=access`.
- Refresh JWT: 7 days, claims `sub`, `type=refresh`.
- Passwords: argon2 via pwdlib. Verification codes: sha256 (short-lived, low-entropy — comment in code).
- `get_current_user` dependency (HTTP Bearer) + `require_admin`.
- Login returns identical 401 for unknown email vs wrong password.

## Cleanup

Celery beat, hourly: `DELETE FROM users WHERE is_verified = false AND created_at < now() - interval '2 days'`.
Core logic in a plain async function so it is unit-testable without a broker.

## Error handling

Domain exceptions in `app/core/exceptions.py` (`EmailAlreadyExistsError`,
`InvalidCredentialsError`, `EmailNotVerifiedError`, `InvalidVerificationCodeError`,
`UserNotFoundError`, `PermissionDeniedError`) mapped to HTTP 409/401/403/400/404/403 by
FastAPI exception handlers registered in `main.py`.

## Project layout

```
users-api/
├── app/
│   ├── main.py                # app factory, routers, exception handlers
│   ├── core/                  # config, database, security, exceptions, celery_app, email
│   └── modules/
│       ├── auth/              # router, service, schemas, dependencies
│       └── users/             # router, service, repository, models, schemas
├── app/tasks.py               # celery cleanup task
├── alembic/, alembic.ini
├── scripts/create_admin.py    # bootstrap first admin
├── tests/                     # integration tests (test PostgreSQL DB)
├── Dockerfile, docker-compose.yml   # api, db, redis, worker, beat
├── .env.example, README.md, pyproject.toml
```

## Delivery

Public GitHub repo; README with quickstart (`docker compose up`), architecture notes,
cleanup logic description; all endpoint summaries/descriptions and code comments in
English; deliberate simplifications flagged with `# SIMPLIFICATION:` comments.
