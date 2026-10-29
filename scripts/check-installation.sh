#!/usr/bin/env bash
# Abschlussprüfung der Installation.
#   CODEWORDS_API_KEY=... HOOK_SECRET=... ./scripts/check-installation.sh
set -uo pipefail

: "${CODEWORDS_API_KEY:?CODEWORDS_API_KEY fehlt}"
BASE="${ILVANA_URL:-https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7}"
AUTH="Authorization: Bearer $CODEWORDS_API_KEY"
fail=0
ok()   { printf '  OK    %s\n' "$1"; }
bad()  { printf '  OFFEN %s\n' "$1"; fail=$((fail+1)); }

echo "1) Dienst erreichbar"
health=$(curl -s -H "$AUTH" "$BASE/health")
echo "  $health" | grep -q '"status":"ok"' && ok "health" || bad "health nicht erreichbar"

version=$(printf '%s' "$health" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null || echo "?")
count=$(curl -s -H "$AUTH" "$BASE/schema/tools" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["tools"]))' 2>/dev/null || echo 0)
[ "$count" -ge 30 ] && ok "Version $version, $count Werkzeuge" || bad "nur $count Werkzeuge (erwartet 30+): $version"

echo "2) Secrets"
info=$(curl -s -X POST "$BASE/tools/service_info" -H "$AUTH" -H 'Content-Type: application/json' -d '{}')
for key in AIRTABLE_PAT HOOK_SECRET ALERT_WEBHOOK_URL; do
  printf '%s' "$info" | grep -q "\"$key\":{\"configured\":true" && ok "$key gesetzt" || bad "$key nicht gesetzt"
done

echo "3) Hook-Schutz"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/hooks/airtable" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"mode":"preview"}')
[ "$code" = "401" ] && ok "ohne Secret gesperrt (401)" || bad "ohne Secret nicht gesperrt (HTTP $code)"

if [ -n "${HOOK_SECRET:-}" ]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/hooks/airtable" -H "$AUTH" \
    -H 'Content-Type: application/json' -d "{\"mode\":\"preview\",\"hook_secret\":\"$HOOK_SECRET\"}")
  [ "$code" = "200" ] && ok "mit Secret freigegeben (200)" || bad "mit Secret abgelehnt (HTTP $code)"
else
  bad "HOOK_SECRET nicht in der Umgebung — Freigabe nicht geprüft"
fi

echo "4) Datenzugriff"
total=$(curl -s -X POST "$BASE/tools/pipeline_summary" -H "$AUTH" -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["total"])' 2>/dev/null || echo 0)
[ "$total" -gt 0 ] && ok "Kopieren lesbar ($total Bewerbungen)" || bad "Kopieren nicht lesbar"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/tools/pipeline_summary" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"base":"original"}')
[ "$code" = "200" ] && ok "Original freigegeben" || bad "Original nicht freigegeben (HTTP $code) — Base im Airtable-Token unter Access ergänzen"

echo
if [ "$fail" -eq 0 ]; then echo "BEREIT"; else echo "$fail Punkt(e) offen"; exit 1; fi
