# Mnema — dev bootstrap kit for macOS

A self-contained kit to set the entire Mnema project up from nothing (Docker →
build → run), create the first administrator, and tear it down — even after
Docker or other tooling has been uninstalled.

The app ships **empty**: no users, no workspaces, no documents. The first
person to open the web UI walks through a `/setup` wizard that creates the
administrator (root system admin) account. Demo data exists only via the
opt-in `--seed-demo` flag, for local demos/development.

## What you need (checked by `doctor`)

| Tool | Install |
|---|---|
| Homebrew | <https://brew.sh> (required for `--install` and easy tooling) |
| Git | `xcode-select --install` or `brew install git` |
| Docker (Desktop) | `brew install --cask docker` — then open Docker Desktop once |
| Docker Compose (v2, ships with Docker Desktop) | CLI + plugin verified by `docker compose version` |

The script checks git, docker, and the compose plugin; with `--install` it
installs anything missing via Homebrew. The Docker engine must be running
(`doctor` will launch Docker Desktop and wait for it).

## Quick start

```bash
# From this repo:
dev/setup.sh setup
```

This:

1. checks prerequisites,
2. clones `https://github.com/procopioos/Mnema.git` into `~/mnema`,
3. writes a fresh `~/mnema/.env` (random `SECRET_KEY` + Postgres password),
4. verifies every file the build needs (see `manifest`),
5. installs frontend dependencies (`npm ci`, skipped if `node_modules` exists
   or `npm` is missing) so editors resolve imports and local `npm run dev`
   works,
6. builds the `api`/`worker`/`web` images and starts the stack (migrations run
   on API start).

Open http://localhost:3000 — you land on `/setup` and create the administrator
account (the first registered user becomes root system admin). No demo data is
loaded unless you pass `--seed-demo`.

Re-running `setup` **resumes**: it reuses the existing `.env` and volumes (and
skips re-cloning), so `down` → `setup` brings the same data back up. Pass
`--force` for a truly fresh start (re-clone + regenerated `.env` + new
volumes).

## Options

```bash
dev/setup.sh setup \
  --source https://github.com/procopioos/Mnema.git \   # what to bootstrap from
  --target ~/mnema \                                   # where to put it
  --project mnema \                                    # compose project namespacing
  --branch main \                                      # branch to clone (default: remote default)
  --copy --source /path/to/checkout \                  # copy a LOCAL checkout (includes uncommitted work)
  --no-clone \                                         # use THIS checkout, in place
  --seed-demo \                                        # load Acme demo data (dev only, known password)
  --skip-check \                                       # skip the prerequisite check
  --force                                              # overwrite non-empty target / skip prompts
```

Overrides for host ports (useful to run several stacks side by side):

```bash
API_PORT=8001 WEB_PORT=3001 POSTGRES_PORT=5433 REDIS_PORT=6380 dev/setup.sh setup ...
```

## Lifecycle

```bash
dev/setup.sh doctor    # check tooling + engine
dev/setup.sh status    # container + API status of the project
dev/setup.sh setup     # fresh bootstrap (see above)
dev/setup.sh down      # stop services (keeps volumes/data)
dev/setup.sh destroy   # down -v + remove volumes/data + remove the target dir
```

`destroy` never removes the source repo (or the current checkout under
`--no-clone`); it only removes the bootstrap target. It prompts unless
`--force` is given.

## First run

The stack starts **empty**. Open `http://localhost:3000`; `/login` detects the
empty database and sends you to `/setup`, where you create the administrator
account. The first registered user becomes **root system admin** and gets an
owner's personal workspace automatically. After `dev/setup.sh destroy` + a
fresh `setup`, the flow repeats — the app is always born blank.

## Demo data (opt-in, dev only)

With `--seed-demo`, the "Acme Consulting" workspace, demo accounts, and five
ready-to-read documents are loaded. On `http://localhost:3000` (web) /
`http://localhost:8000/docs` (API):

| Email | Role |
|---|---|
| `alex@acme.example` | owner **+ root system admin** |
| `casey@acme.example` | admin |
| `mara@acme.example` | manager |
| `sam@acme.example` | employee |

Shared demo password: `Acme!demo2026` (known, public — never use this on a
reachable deployment).

## Files here

- `setup.sh` — the whole bootstrap as a single bash script.
- `env.template` — `.env` skeleton; `__SECRET_KEY__`, `__POSTGRES_PASSWORD__`,
  `__COMPOSE_PROJECT_NAME__` are replaced with generated values at setup time.
- `manifest` — every file the setup requires inside the checkout; verified
  after cloning/copying so a broken or incomplete source fails fast.
- `README.md` — this file.

The actual build/run configuration is **not** duplicated here: `setup.sh`
consumes the project's own `docker-compose.yml`, `backend/Dockerfile`,
`frontend/Dockerfile` and `scripts/docker-entrypoint.sh` straight from the
checkout (that's what `manifest` verifies), so there is a single source of
truth. `backend/scripts/seed_demo.py` (the opt-in demo seed) also ships in the
checkout but is never called unless `--seed-demo` is passed.

## Troubleshooting

- **Port already in use** (`address already in use`): a dev server or another
  Mnema stack is on that port. Stop it, or override the port
  (`API_PORT=8010 WEB_PORT=3010 ...`) / use a different `--project`.
- **API never becomes healthy**: `cd ~/mnema && docker compose logs api`.
  Migrations run on API start; a fresh Postgres volume can take a few seconds.
- **Docker Desktop shows "engine stopped"**: open Docker Desktop, wait for the
  whale to go green, re-run.
- **A stale stack from an older container naming**: renames are
  project-scoped (`${COMPOSE_PROJECT_NAME}-*`); run
  `docker compose up -d --remove-orphans` in the target to sweep the old ones.
- **A fresh clone from GitHub is missing recent work**: commits must be pushed
  first. Until then use `--copy` with a local checkout to include uncommitted
  files.
- **Editor shows red / "cannot find module"**: `frontend/node_modules` is
  missing (fresh clones exclude it). Re-run `dev/setup.sh setup` (it installs
  them) or `cd frontend && npm ci` by hand, then reload the editor window.
- **API/worker crash-loop with `password authentication failed for user
  "mnema"`**: the `.env` password doesn't match the reused Postgres volume
  (fresh credentials + old data). Re-run `setup`: it now wipes the project
  volumes under `--force`, or aborts with instructions when the password is
  unrecoverable.
- **Two checkouts, one project name** (e.g. `~/mnema` vs `.../Desktop/Mnema`
  both sanitize to `mnema`): they share containers and volumes. `setup` warns
  when another checkout's containers are running — stop that stack first, or
  pass a distinct `--project`.