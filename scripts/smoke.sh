#!/usr/bin/env bash
# Mnema smoke test: register -> upload a real PDF -> wait for processing ->
# print pages -> verify the stored file. Prints the UUIDs you need to keep
# poking at the API afterwards.
#
# Prereqs: Docker infra up (`docker compose up -d`) and the API + worker
# running (`cd backend && uv run honcho start`).
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"
API="$BASE/api/v1"
EMAIL="${EMAIL:-smoke-$(date +%s)@example.com}"
PASSWORD="password123"
PDF="$(mktemp /tmp/mnema-smoke-XXXXXX.pdf)"

cd "$(dirname "$0")/.."

echo "==> Generating a 2-page PDF fixture"
(
  cd backend
  uv run python - "$PDF" <<'PY'
import sys
import pymupdf

doc = pymupdf.open()
p = doc.new_page()
p.insert_text((72, 72), "Mnema smoke test: onboarding basics, vacation policy on page one.", fontsize=12)
p2 = doc.new_page()
p2.insert_text((72, 72), "Page two: employees get 25 paid vacation days.", fontsize=12)
doc.save(sys.argv[1])
PY
)

echo "==> Registering $EMAIL"
REG=$(curl -s -X POST "$API/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Smoke Tester\"}")
TOKEN=$(echo "$REG" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
WS=$(echo "$REG" | python3 -c "import sys,json;print(json.load(sys.stdin)['workspace_id'])")
echo "    workspace_id: $WS"

echo "==> Uploading document"
DOC=$(curl -s -X POST "$API/workspaces/$WS/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$PDF;type=application/pdf" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "    document_id: $DOC"

echo "==> Waiting for processing"
for _ in $(seq 1 15); do
  STATUS=$(curl -s "$API/documents/$DOC" -H "Authorization: Bearer $TOKEN" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  echo "    status: $STATUS"
  [ "$STATUS" = ready ] && break
  [ "$STATUS" = failed ] && { echo "FAILED" >&2; exit 1; }
  sleep 1
done

echo "==> Pages"
curl -s "$API/documents/$DOC/pages" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "==> Stored file bytes: $(curl -s "$API/documents/$DOC/file" -H "Authorization: Bearer $TOKEN" | wc -c | tr -d ' ')"

echo
echo "==> Copy-paste ready (for Swagger / curl)"
echo "    email:        $EMAIL"
echo "    password:     $PASSWORD"
echo "    token:        $TOKEN"
echo "    workspace_id: $WS"
echo "    document_id:  $DOC"

rm -f "$PDF"