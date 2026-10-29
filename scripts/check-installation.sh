#!/usr/bin/env bash
# Abschlussprüfung der Installation.
#   CODEWORDS_API_KEY=... HOOK_SECRET=... ./scripts/check-installation.sh
set -uo pipefail

: "${CODEWORDS_API_KEY:?CODEWORDS_API_KEY fehlt}"
BASE="${ILVANA_URL:-https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7}"
AUTH="Authorization: Bearer $CODEWORDS_API_KEY"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

post() { curl -s -m 60 -X POST "$BASE/tools/$1" -H "$AUTH" -H 'Content-Type: application/json' -d "${2:-{\}}"; }

# alle Abfragen parallel starten
curl -s -m 60 -H "$AUTH" "$BASE/health"                                  > "$tmp/health" &
curl -s -m 60 -H "$AUTH" "$BASE/schema/tools"                            > "$tmp/tools" &
post service_info '{}'                                                   > "$tmp/info" &
post pipeline_summary '{}'                                               > "$tmp/pipe" &
curl -s -m 60 -o /dev/null -w '%{http_code}' -X POST "$BASE/hooks/airtable" -H "$AUTH" \
     -H 'Content-Type: application/json' -d '{"mode":"preview"}'          > "$tmp/h_no" &
post pipeline_summary '{"base":"original"}' -o /dev/null -w '%{http_code}' > "$tmp/orig" &
if [ -n "${HOOK_SECRET:-}" ]; then
  curl -s -m 60 -o /dev/null -w '%{http_code}' -X POST "$BASE/hooks/airtable" -H "$AUTH" \
       -H 'Content-Type: application/json' \
       -d "{\"mode\":\"preview\",\"hook_secret\":\"$HOOK_SECRET\"}"       > "$tmp/h_yes" &
fi
wait

fail=0
ok()  { printf '  OK     %s\n' "$1"; }
bad() { printf '  OFFEN  %s\n' "$1"; fail=$((fail+1)); }

echo "1) Dienst"
grep -q '"status":"ok"' "$tmp/health" && ok "health" || bad "health nicht erreichbar"
version=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$tmp/health" 2>/dev/null || echo "?")
count=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["tools"]))' "$tmp/tools" 2>/dev/null || echo 0)
[ "$count" -ge 30 ] && ok "Version $version, $count Werkzeuge" || bad "nur $count Werkzeuge (erwartet 30+)"

echo "2) Secrets"
info=$(cat "$tmp/info")
for key in AIRTABLE_PAT HOOK_SECRET ALERT_WEBHOOK_URL; do
  printf '%s' "$info" | grep -q "\"$key\":{\"configured\":true" && ok "$key gesetzt" || bad "$key nicht gesetzt"
done

echo "3) Hook-Schutz"
[ "$(cat "$tmp/h_no")" = "401" ] && ok "ohne Secret gesperrt (401)" || bad "ohne Secret nicht gesperrt (HTTP $(cat "$tmp/h_no"))"
if [ -f "$tmp/h_yes" ]; then
  [ "$(cat "$tmp/h_yes")" = "200" ] && ok "mit Secret freigegeben (200)" || bad "mit Secret abgelehnt (HTTP $(cat "$tmp/h_yes"))"
else
  bad "HOOK_SECRET nicht in der Umgebung — Freigabe nicht geprüft"
fi

echo "4) Datenzugriff"
total=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["result"]["total"])' "$tmp/pipe" 2>/dev/null || echo 0)
[ "$total" -gt 0 ] && ok "Kopieren lesbar ($total Bewerbungen)" || bad "Kopieren nicht lesbar"
[ "$(cat "$tmp/orig")" = "200" ] && ok "Original freigegeben" \
  || bad "Original nicht freigegeben (HTTP $(cat "$tmp/orig")) — Base im Airtable-Token unter Access ergänzen"

echo
if [ "$fail" -eq 0 ]; then echo "BEREIT"; else echo "$fail Punkt(e) offen"; exit 1; fi
