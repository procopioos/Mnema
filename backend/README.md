# Mnema Backend

The Mnema API: a FastAPI service for a document knowledge base. Async SQLAlchemy + `asyncpg`, Alembic migrations, JWT auth (Argon2 password hashing), and an Arq worker for background document ingestion backed by Redis + Postgres.

## Stack

- **Python 3.14 + FastAPI** (uv package manager)
- **SQLAlchemy 2** (async) + **asyncpg** + **Alembic**
- **Postgres 16** and **Redis 7** (via `docker-compose.yml`)
- **Arq** worker for background ingestion
- **JWT** access/refresh tokens, **Argon2** password hashing

## API surface

Interactive docs at `http://127.0.0.1:8000/docs` (OpenAPI). Endpoints under `/api/v1`:

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| Workspaces | `GET /workspaces`, `POST /workspaces`, `GET/PATCH/DELETE /workspaces/{id}`, `GET /workspaces/{id}/members` |
| Membership | `GET /workspaces/{id}/members`, `PATCH/DELETE /workspaces/{id}/members/{member_user_id}` (RBAC: owner/admin/manager/employee) |
| Folders | `GET/POST /workspaces/{id}/folders`, `PATCH/DELETE /folders/{id}` |
| Tags | `GET/POST /workspaces/{id}/tags`, `PATCH/DELETE /tags/{id}` (workspace-global or per-user) |
| Documents | `GET /workspaces/{id}/documents`, `GET /documents/public`, `POST /workspaces/{id}/documents` (upload), `GET/PATCH/DELETE /documents/{id}`, `PUT /documents/{id}/folders`, `PUT /documents/{id}/tags`, `GET /documents/{id}/pages`, `GET /documents/{id}/pages/{n}`, `GET /documents/{id}/file` |
| Audit log | `GET /workspaces/{id}/audit`, `GET /admin/audit` |
| Admin | `POST /admin/reset`, `GET /admin/stats`, `GET /admin/users`, `PATCH /admin/users/{id}`, `GET/POST/PATCH/DELETE /admin/workspaces...`, `GET/POST/PATCH/DELETE /admin/workspaces/{id}/members...` |

Supported file types: PDF, DOCX, TXT, Markdown.

## Getting started

### 1. Infra

```bash
docker compose up -d
```

### 2. Dev server (API + worker together)

```bash
cd backend && uv run honcho start
```

Standalone equivalents: `uv run uvicorn app.main:app --reload` (API) and `uv run arq app.workers.worker.WorkerSettings` (worker).

### 3. Migrations

```bash
cd backend && uv run alembic upgrade head
```

### 4. Tests

```bash
cd backend && uv run pytest
```

### 5. Lint / format

```bash
cd backend && uv run ruff check .
uv run ruff format .
```

## Demo data

Seed an "Acme Consulting" workspace with users, folders, tags and ready documents (root admin owner + admin/manager/employee members, all with password `Acme!demo2026`):

```bash
cd backend
uv run python -m scripts.seed_demo
```

Re-running after success is a no-op (`--force` skips the exists-check). Requires migrated schema and Redis up (for the worker). The first registered user becomes the root system admin, so the seed also exercises the admin console.

## Reset

```bash
# Wipes all data and storage (root only)
curl -X POST http://127.0.0.1:8000/api/v1/admin/reset -H "Authorization: Bearer <root-token>"
```

## Storage, backups, S3

Files live under `STORAGE_DIR` (default `backend/data`; mounted as a named volume in Docker). Back up the Postgres database plus this directory:

```bash
docker compose exec postgres pg_dump -U mnema mnema > backup.sql
```

To move storage to S3, implement the `StorageBackend` ABC (`app/infrastructure/storage.py`: `save/open/delete/exists/clear_all`) and return your `S3Storage` from `get_storage()` — the rest of the app is storage-agnostic.

## Project layout

```text
backend/
├── app/
│   ├── api/v1/          # FastAPI routers (auth, workspaces, documents, admin)
│   ├── core/            # config, security (JWT/Argon2), dependencies
│   ├── db/              # SQLAlchemy session + base
│   ├── domain/          # exceptions, allowed formats, roles
│   ├── infrastructure/  # storage backend, queue (Arq)
│   ├── models/          # SQLAlchemy models (user, workspace, document, ...)
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # auth, workspaces, documents, ingestion pipeline/extractors
│   └── workers/         # Arq tasks + worker settings
├── alembic/             # migrations
├── scripts/             # docker-entrypoint, seed_demo
├── tests/               # pytest suite (105 passing)
├── Dockerfile           # api/worker image (runs migrations on start)
├── Procfile             # honcho: api + worker
└── pyproject.toml
```