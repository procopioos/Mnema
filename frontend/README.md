# Mnema Frontend

The Mnema web app: a document knowledge base UI. Built with **Next.js 16 + TypeScript + Tailwind CSS v4 + shadcn/ui** (Radix). It talks to the [FastAPI backend](../backend/README.md) through a `/api/:path*` dev proxy.

## Stack

- **Next.js 16** (App Router, Turbopack) + React 19
- **Tailwind CSS v4** (CSS-first config in `app/globals.css`) with **shadcn/ui** components (`components/ui/`)
- **Fonts**: Apple system sans stack for body/headings (SF Pro on Apple devices, system-ui fallback) + JetBrains Mono via `next/font/google` for code, status data and preview text — wired in `app/layout.tsx` and `app/globals.css`
- **`docx-preview`** — DOCX rendering in the browser
- **`react-markdown` + `remark-gfm`** — Markdown rendering with GitHub-flavored extensions
- **`@tailwindcss/typography`** — `prose` styling for rendered Markdown

## Routes

| Path | Description |
|---|---|
| `/login` | Sign in |
| `/register` | Create account |
| `/` | Dashboard (document count, recent documents) |
| `/documents` | Upload (button + drag & drop), list with status badges, delete |
| `/documents/[id]` | Document viewer |
| `/admin` | Admin console (system admins only): stats, user management, workspace management, audit log |

Document pages live under the `(app)` route group and load data via the `useAuth()` context (`lib/auth-context.tsx`), which restores the session (user + `workspaceId`) on page load from stored tokens.

## Admin console

`app/(app)/admin/page.tsx` is guarded by `RequireAdmin` (from `components/app-shell.tsx`); non-root/`is_system_admin` users are redirected out. It offers four tabs:

- **Overview** — global stats (`/admin/stats`) and per-workspace usage
- **Users** — search, promote/demote admins (root users are protected from demotion)
- **Workspaces** — create (with owner + quota caps), rename, edit quota, manage members/roles, delete
- **Activity** — the full audit log with a workspace filter

## Document viewer

The viewer (`app/(app)/documents/[id]/page.tsx`) shows a **Text** tab (extracted pages from the backend) plus one preview mode, chosen by file type:

- **PDF** (`application/pdf`) → inline iframe using the authenticated file blob
- **DOCX** → `docx-preview` renders the document in-browser (styles, tables, images)
- **Markdown** (`text/markdown`) → rendered HTML via `react-markdown` (GFM, `prose` styling)
- **TXT** (`text/plain`) → raw text in a scrollable `<pre>`

## Getting started

### Install

```bash
npm install
```

### Run the dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The `/api/:path*` rewrite proxies to the backend (default `http://127.0.0.1:8000`, override with the `API_PROXY` env var). See `next.config.ts`.

### Full stack (backend + worker + frontend)

From the repository root:

```bash
backend/.venv/bin/honcho start
```

Starts the API (`:8000`), Arq worker, and frontend (`:3000`).

### Full stack in Docker

```bash
docker compose up -d --build
```

Builds all three services (`api` → `:8000`, `worker`, `web` → `:3000`). The API runs Alembic migrations on start. The app starts empty — the first visitor is routed to `/setup` to create the administrator account. Demo data is opt-in: `docker compose exec api uv run python -m scripts.seed_demo`.

## Useful commands

```bash
npm run dev       # dev server (Turbopack)
npm run build     # production build
npm run lint      # ESLint
npm run typegen   # regenerate lib/api/generated.d.ts from backend OpenAPI (backend must run on :8000)
npx tsc --noEmit  # typecheck
```

## Notes

- The dev config (`next.config.ts`) sets `allowedDevOrigins` to `["127.0.0.1", "localhost"]` so Turbopack serves JS chunks when using either host.
- The 401-handling, token storage, and auto-refresh live in `lib/api.ts`; API request/response types are generated into `lib/api/generated.d.ts` by `npm run typegen`.