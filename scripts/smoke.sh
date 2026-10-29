#!/usr/bin/env bash
# Smoke-Test gegen den laufenden Dienst.
# Verwendung: CODEWORDS_API_KEY=... ./scripts/smoke.sh
set -euo pipefail

: "${CODEWORDS_API_KEY:?CODEWORDS_API_KEY fehlt}"
BASE="${ILVANA_URL:-https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7}"
AUTH="Authorization: Bearer $CODEWORDS_API_KEY"

echo "1/3 health"
code=$(curl -s -o /dev/null -w '%{http_code}' -H "$AUTH" "$BASE/health")
[ "$code" = "200" ] || { echo "  FAIL health=$code"; exit 1; }
echo "  ok"

echo "2/3 Werkzeugliste"
count=$(curl -s -H "$AUTH" "$BASE/schema/tools" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)["tools"]))')
[ "$count" -ge 31 ] || { echo "  FAIL nur $count Werkzeuge"; exit 1; }
echo "  ok ($count Werkzeuge)"

echo "3/3 Lesetest"
out=$(curl -s -X POST "$BASE/tools/pipeline_summary" -H "$AUTH" \
      -H 'Content-Type: application/json' -d '{}')
echo "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d["success"]; print("  ok,", d["result"]["total"], "Bewerbungen")'

echo "Smoke-Test bestanden."
