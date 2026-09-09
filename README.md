# Mnema — your local, totally private, document server.

Mnema is a self-hosted document knowledge base: upload PDFs, DOCX, Markdown or TXT, and Mnema extracts the text into pages you can read, search and share privately across your workspace.

- **Backend** — FastAPI + Postgres + Redis + Arq (see [`backend/README.md`](backend/README.md))
- **Frontend** — Next.js 16 + Tailwind (see [`frontend/README.md`](frontend/README.md))
- **Auth** — JWT with Argon2 password hashing, RBAC (owner/admin/manager/employee) + system admins
- **Workspaces** — members, folders, tags, per-workspace quotas (documents & storage)
- **Audit log** — events for auth, workspaces, documents and admin actions

## Quick start (Docker — everything)

```bash
cp .env.example .env
docker compose up -d --build
```

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs
- Migrations run automatically when the API container starts; storage lives in the `storage_data` volume.

The app starts **empty**. Open http://localhost:3000 — you're sent to `/setup`
to create the administrator account (the first registered user becomes the
root system admin). To load the optional "Acme Consulting" demo workspace
(dev only, known public password):

```bash
docker compose exec api uv run python -m scripts.seed_demo
```

## Quick start (local dev)

```bash
cp .env.example backend/.env
docker compose up -d            # Postgres + Redis only
cd backend && uv run honcho start   # API :8000 + worker
cd frontend && npm install && npm run dev   # UI :3000
```

## Useful scripts

- `scripts/smoke.sh` — end-to-end smoke test against the running API (`:8000`)
- `POST /api/v1/admin/reset` — wipe all data and storage (root only)
- `uv run python -m scripts.seed_demo` — seed demo data (see backend README)

## Backups

Postgres + `STORAGE_DIR` are your data. See [`backend/README.md`](backend/README.md) for `pg_dump` and moving storage to S3.