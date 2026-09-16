#!/usr/bin/env bash
# Mnema dev bootstrap kit for macOS.
#
# Sets the whole project up from scratch: prerequisites -> fresh source ->
# env -> Docker images -> containers -> migrations -> editor deps. The app
# starts EMPTY;
# the first visitor creates the administrator account in the UI or via
# --seed-demo (demo data, dev only).
#
# Subcommands:
#   setup     (default) full bootstrap from a fresh source into TARGET
#   doctor    check prerequisites (git, docker, compose, daemon)
#   status    show container + API status
#   down      stop the stack (keeps data)
#   destroy   stop, wipe volumes and data, remove TARGET (--force to skip the prompt)
#
# Flags:
#   --install        auto-install missing prerequisites via Homebrew
#   --no-clone       operate on the current checkout (dev/ lives in it) instead of cloning
#   --copy           SOURCE is a local directory; rsync it (includes uncommitted work)
#   --source URL|DIR repo to bootstrap from (default GitHub)
#   --target DIR     target directory (default ~/mnema)
#   --project NAME   compose project name for container/volume namespacing
#   --branch BR      git branch for clone (default: remote's default branch)
#   --seed-demo      load the Acme Consulting demo data (dev only, known password!)
#   --skip-seed      deprecated no-op: booting empty is the default now
#   --skip-check     skip the prerequisite/daemon check
#   --force          bypass safety prompts (used by destroy / non-empty target)
#   --help
#
# @procopioos 2026-09-10 (yyyy-mm-dd)
# Host ports are overridable via API_PORT / WEB_PORT / POSTGRES_PORT / REDIS_PORT.

set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${KIT_DIR}/.." && pwd)"
MANIFEST="${KIT_DIR}/manifest"
ENV_TEMPLATE="${KIT_DIR}/env.template"

DEFAULT_SOURCE="https://github.com/procopioos/Mnema.git"
DEFAULT_TARGET="${HOME}/mnema"

SOURCE="${DEFAULT_SOURCE}"
TARGET=""
PROJECT=""
BRANCH=""
INSTALL=0
NO_CLONE=0
COPY=0
SEED_DEMO=0
SKIP_CHECK=0
FORCE=0
CMD="setup"

log()  { printf '\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; 1>&2; }
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# *//'
  exit 0
}

[ $# -ge 1 ] && case "$1" in
  setup|doctor|status|down|destroy) CMD="$1"; shift ;;
  -h|--help|help) usage ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --install) INSTALL=1 ;;
    --no-clone) NO_CLONE=1 ;;
    --copy) COPY=1 ;;
    --seed-demo) SEED_DEMO=1 ;;
    --skip-seed) warn "--skip-seed is the default now; use --seed-demo to load demo data" ;;
    --skip-check) SKIP_CHECK=1 ;;
    --force) FORCE=1 ;;
    --source) SOURCE="${2:?--source needs a value}"; shift ;;
    --target) TARGET="${2:?--target needs a value}"; shift ;;
    --project) PROJECT="${2:?--project needs a value}"; shift ;;
    --branch) BRANCH="${2:?--branch needs a value}"; shift ;;
    -h|--help) usage ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

if [ "${NO_CLONE}" -eq 1 ] && [ "${COPY}" -eq 1 ]; then
  die "--no-clone and --copy are mutually exclusive"
fi

# ---------------------------------------------------------------------------
# doctor: prerequisites
# ---------------------------------------------------------------------------
prereq_missing() {
  local tool="$1" install_cmd="$2"
  if command -v "${tool}" >/dev/null 2>&1; then return 1; fi
  if [ "${INSTALL}" -eq 1 ]; then
    log "Installing ${tool} via Homebrew"
    brew install "${install_cmd}"
  else
    die "${tool} is missing. Install it with: ${install_cmd}"
  fi
  return 0
}

doctor() {
  command -v brew >/dev/null 2>&1 \
    || die "Homebrew is required (https://brew.sh). Install it, then re-run."

  prereq_missing git "git" || true
  prereq_missing docker "docker" || true

  if ! command -v docker >/dev/null 2>&1; then
    : # just installed docker (CLI); compose/daemon checks below will guide
  fi

  if ! docker compose version >/dev/null 2>&1; then
    if command -v docker >/dev/null 2>&1 && [ -d "/Applications/Docker.app" ]; then
      warn "docker CLI lacks the compose plugin (v2). Reinstall Docker Desktop:"
      warn "  brew uninstall --cask docker && brew install --cask docker"
      exit 1
    fi
    die "docker compose is missing. Install Docker Desktop:  brew install --cask docker"
  fi

  if ! docker info >/dev/null 2>&1; then
    warn "Docker engine is not running."
    if [ -d "/Applications/Docker.app" ]; then
      log "Starting Docker Desktop"
      open -a Docker
    fi
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
      docker info >/dev/null 2>&1 && break
      warn "waiting for the Docker engine... (open Docker Desktop if it stays stuck)"
      sleep 5
    done
    docker info >/dev/null 2>&1 || die "Docker engine is not responding. Open Docker Desktop and re-run."
  fi
  log "Prerequisites OK (git, docker, compose)"
}

# ---------------------------------------------------------------------------
# manifest verification
# ---------------------------------------------------------------------------
verify_manifest() {
  local root="$1" missing miss
  log "Verifying project files (manifest)"
  miss=0
  while IFS= read -r line; do
    case "$line" in '' | \#*) continue ;; esac
    case "$line" in
      */) [ -d "${root}/${line}" ] || { warn "missing dir:  ${line}"; miss=1; } ;;
      *)  [ -f "${root}/${line}" ] || { warn "missing file: ${line}"; miss=1; } ;;
    esac
  done < "${MANIFEST}"
  [ "${miss}" -eq 0 ] || die "the bootstrap source is missing required files (above)"
  # Light sanity: the file that must contain the compose services.
  grep -q "services:" "${root}/docker-compose.yml" || die "docker-compose.yml looks malformed"
  grep -q 'container_name' "${root}/docker-compose.yml" || die "docker-compose.yml missing container_name"
  log "Manifest OK"
}

# ---------------------------------------------------------------------------
# target / source materialization
# ---------------------------------------------------------------------------
sanitize_project() {
  local base
  base="$(basename "${1}")"
  printf '%s' "${base}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g; s/^-+|-+$//g'
}

prepare_target() {
  if [ "${NO_CLONE}" -eq 1 ]; then
    TARGET="${REPO_ROOT}"
    [ -z "${PROJECT}" ] && PROJECT="$(sanitize_project "${TARGET}")"
    log "Using current checkout in place: ${TARGET}"
    return
  fi

  [ -z "${TARGET}" ] && TARGET="${DEFAULT_TARGET}"
  [ -z "${PROJECT}" ] && PROJECT="$(sanitize_project "${TARGET}")"

  if [ -e "${TARGET}" ] && [ -n "$(ls -A "${TARGET}" 2>/dev/null || true)" ]; then
    if [ "${FORCE}" -eq 1 ]; then
      warn "Target ${TARGET} is not empty; removing it (--force) for a fresh start"
      rm -rf "${TARGET}"
    else
      log "Resuming existing target ${TARGET} (reuses .env + volumes; --force for a fresh start)"
      return
    fi
  fi

  mkdir -p "$(dirname "${TARGET}")"
  case "${SOURCE}" in
    *://* | git@* ) # remote URL
      if [ -n "${BRANCH}" ]; then
        log "Cloning ${SOURCE} (branch ${BRANCH}, depth 1) -> ${TARGET}"
      else
        log "Cloning ${SOURCE} (default branch, depth 1) -> ${TARGET}"
      fi
      git clone --depth 1 ${BRANCH:+--branch "${BRANCH}"} "${SOURCE}" "${TARGET}"
      ;;
    */) die "local --source path should not end with '/': ${SOURCE}" ;;
    *) # local path
      [ -d "${SOURCE}" ] || die "local --source directory not found: ${SOURCE}"
      if [ "${COPY}" -eq 1 ]; then
        log "Copying ${SOURCE} -> ${TARGET}"
        command -v rsync >/dev/null 2>&1 || die "rsync is required for --copy"
        rsync -a \
          --exclude '.git/' --exclude '.venv/' --exclude 'node_modules/' \
          --exclude '.next/' --exclude 'data/' --exclude 'data-test/' \
          --exclude '.DS_Store' --exclude '*.log' --exclude 'session-*.md' \
          --exclude '.ruff_cache/' --exclude '.pytest_cache/' \
          --exclude '__pycache__/' \
          "${SOURCE}/" "${TARGET}/"
      else
        log "Cloning local checkout ${SOURCE} -> ${TARGET}"
        git clone --depth 1 ${BRANCH:+--branch "${BRANCH}"} "${SOURCE}" "${TARGET}"
      fi
      ;;
  esac
}

write_env() {
  local envfile="${TARGET}/.env"
  if [ -f "${envfile}" ] && [ "${FORCE}" -eq 0 ]; then
    warn "Keeping existing ${envfile} (pass --force to regenerate)"
    return
  fi
  log "Generating ${envfile} (random credentials)"
  local secret dbpass
  secret="$(openssl rand -hex 32)"
  dbpass="$(openssl rand -hex 16)"
  sed -e "s/__COMPOSE_PROJECT_NAME__/${PROJECT}/g" \
      -e "s/__SECRET_KEY__/${secret}/g" \
      -e "s/__POSTGRES_PASSWORD__/${dbpass}/g" \
      "${ENV_TEMPLATE}" > "${envfile}"
  chmod 600 "${envfile}"
}

# ---------------------------------------------------------------------------
# frontend deps (editor + local `npm run dev`; the Docker image builds its own)
# ---------------------------------------------------------------------------
install_frontend_deps() {
  local fdir="${TARGET}/frontend"
  [ -f "${fdir}/package.json" ] || { warn "no frontend/package.json; skipping editor deps"; return 0; }
  if [ -d "${fdir}/node_modules" ]; then
    log "frontend/node_modules present; skipping npm install"
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    warn "npm is missing; skipping frontend deps (the editor will show unresolved imports)."
    warn "Install node (brew install node) then run: cd ${fdir} && npm ci"
    return 0
  fi
  log "Installing frontend dependencies (npm ci) for the editor + local dev"
  (cd "${fdir}" && npm ci)
}

# ---------------------------------------------------------------------------
# stack lifecycle
# ---------------------------------------------------------------------------
up_stack() {
  log "Building images (api, worker, web)"
  docker compose --project-directory "${TARGET}" -f "${TARGET}/docker-compose.yml" build
  log "Starting services"
  docker compose --project-directory "${TARGET}" -f "${TARGET}/docker-compose.yml" up -d --remove-orphans
}

wait_api() {
  local port="${API_PORT:-8000}" tries=0
  log "Waiting for API on :${port}"
  until curl -fsS "http://127.0.0.1:${port}/api/v1/health" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "${tries}" -ge 36 ]; then
      warn "API did not become healthy in ~3 minutes. Inspect with:"
      warn "  cd ${TARGET} && docker compose logs api"
      return 1
    fi
    sleep 5
  done
  log "API healthy"
}

seed() {
  log "Seeding demo data (Acme Consulting)"
  docker compose --project-directory "${TARGET}" -f "${TARGET}/docker-compose.yml" exec -T api \
    uv run python -m scripts.seed_demo
}

verify_demo() {
  local port="${API_PORT:-8000}" base resp
  base="http://127.0.0.1:${port}/api/v1"
  resp="$(curl -s -X POST "${base}/auth/login" -H 'Content-Type: application/json' \
    -d '{"email":"alex@acme.example","password":"Acme!demo2026"}')"
  local token
  token="$(printf '%s' "${resp}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])' 2>/dev/null || true)"
  if [ -z "${token}" ]; then
    warn "Could not log in as the demo owner (seed may have been skipped)."
    return 0
  fi
  log "Verifying demo data"
  local tries=0 ready=0 total=0
  while [ "${tries}" -lt 12 ]; do
    ready="$(curl -s "${base}/admin/stats" -H "Authorization: Bearer ${token}" \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["documents"]["ready"])' 2>/dev/null || echo 0)"
    total="$(curl -s "${base}/admin/stats" -H "Authorization: Bearer ${token}" \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["documents"]["total"])' 2>/dev/null || echo 0)"
    [ "${ready}" -ge "${total}" ] && [ "${total}" -gt 0 ] && break
    sleep 5
    tries=$((tries + 1))
  done
  curl -s "${base}/admin/stats" -H "Authorization: Bearer ${token}" \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("  users: %d  workspaces: %d  documents: %d  ready: %d" % (d["users"], d["workspaces"], d["documents"]["total"], d["documents"]["ready"]))'
  [ "${ready}" -ge "${total}" ] && [ "${total}" -gt 0 ] \
    || warn "some documents are still processing; re-check with: dev/setup.sh status"
}

summary() {
  local web="${WEB_PORT:-3000}" api="${API_PORT:-8000}"
  cat <<EOF

Mnema is up and running.

  Web UI:        http://localhost:${web}
  API docs:      http://localhost:${api}/docs
  Project:       ${PROJECT}  (compose project; dir: ${TARGET})
EOF
  if [ "${SEED_DEMO}" -eq 1 ]; then
    cat <<EOF

Demo accounts (password: Acme!demo2026):
  alex@acme.example   owner + root system admin
  casey@acme.example  admin
  mara@acme.example   manager
  sam@acme.example    employee
EOF
  else
    cat <<EOF

Fresh install: open http://localhost:${web} and create the administrator
account. The first user to register becomes the root system admin.
EOF
  fi
  cat <<EOF

Manage:
  ${KIT_DIR}/setup.sh status    # health + status
  ${KIT_DIR}/setup.sh down      # stop services (data kept)
  ${KIT_DIR}/setup.sh destroy   # stop + wipe volumes/data + remove ${TARGET}
EOF
}

# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
cmd_setup() {
  if [ "${SKIP_CHECK}" -eq 0 ]; then doctor; fi
  prepare_target
  write_env
  verify_manifest "${TARGET}"
  install_frontend_deps
  up_stack
  wait_api || {
    warn "API failed to come up. Diagnostics:"
    warn "  cd ${TARGET} && docker compose logs api"
    exit 1
  }
  if [ "${SEED_DEMO}" -eq 1 ]; then
    seed
    verify_demo
  else
    log "Fresh install ready (no demo data): create the administrator account at http://localhost:${WEB_PORT:-3000}"
  fi
  summary
}

cmd_status() {
  local dir="${TARGET:-${REPO_ROOT}}"
  if [ -f "${dir}/docker-compose.yml" ]; then
    docker compose --project-directory "${dir}" -f "${dir}/docker-compose.yml" ps
  else
    warn "no docker-compose.yml found; pass --target <dir>"
    exit 1
  fi
  local api="${API_PORT:-8000}"
  curl -fsS "http://127.0.0.1:${api}/api/v1/health" >/dev/null 2>&1 \
    && log "API :${api} OK" || warn "API :${api} not responding"
}

cmd_down() {
  local dir="${TARGET:-${REPO_ROOT}}"
  [ -f "${dir}/docker-compose.yml" ] || die "no docker-compose.yml at ${dir}; pass --target"
  docker compose --project-directory "${dir}" -f "${dir}/docker-compose.yml" down
}

cmd_destroy() {
  local dir="${TARGET:-${REPO_ROOT}}"
  [ -f "${dir}/docker-compose.yml" ] || die "no docker-compose.yml at ${dir}; pass --target"
  log "Stopping services and removing volumes (data WILL be lost)"
  docker compose --project-directory "${dir}" -f "${dir}/docker-compose.yml" down -v
  if [ "${NO_CLONE}" -eq 1 ]; then
    log "Keeping the current checkout (--no-clone): ${dir}"
    return
  fi
  if [ "${FORCE}" -eq 0 ]; then
    printf 'Remove the target directory (%s)? [y/N] ' "${dir}"
    read -r answer
    case "${answer}" in y | Y | yes | YES) ;; *) echo "Keeping ${dir}"; return ;; esac
  fi
  rm -rf "${dir}"
  log "Removed ${dir}"
}

case "${CMD}" in
  setup)   cmd_setup ;;
  doctor)  doctor ;;
  status)  cmd_status ;;
  down)    cmd_down ;;
  destroy) cmd_destroy ;;
esac