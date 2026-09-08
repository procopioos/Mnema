#!/bin/sh
set -e

# Run pending migrations on every start so `docker compose up` is enough for a
# fresh clone. Alembic is idempotent: it applies only missing revisions.
echo "==> Applying migrations"
uv run alembic upgrade head

echo "==> Starting: $*"
exec "$@"