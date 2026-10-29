#!/usr/bin/env bash
# Statusbericht für den Ilvana-Stack.
#   CODEWORDS_API_KEY=... ./scripts/monitor.sh
set -uo pipefail

: "${CODEWORDS_API_KEY:?CODEWORDS_API_KEY fehlt}"
MCP="${ILVANA_URL:-https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7}"
NOTION="${NOTION_URL:-https://runtime.codewords.ai/run/ilvana_notion_sync_0468633e}"
AUTH="Authorization: Bearer $CODEWORDS_API_KEY"
fail=0
ok()  { printf '  OK    %s\n' "$1"; }
bad() { printf '  FEHLER %s\n' "$1"; fail=$((fail+1)); }

echo "Ilvana MCP — $(date '+%Y-%m-%d %H:%M')"
start=$(date +%s)
health=$(curl -s -m 30 -H "$AUTH" "$MCP/health")
ms=$(( $(date +%s) - start ))
version=$(printf '%s' "$health" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null || echo "?")
tools=$(printf '%s' "$health" | python3 -c 'import sys,json;print(json.load(sys.stdin)["tools"])' 2>/dev/null || echo 0)
[ "$tools" -ge 31 ] && ok "Version $version, $tools Werkzeuge, ${ms}s" || bad "nur $tools Werkzeuge (erwartet 31)"

mcp=$(curl -s -m 30 -H "$AUTH" -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"monitor","version":"1"}}}' \
      "$MCP/mcp/")
printf '%s' "$mcp" | grep -q '"serverInfo"' && ok "MCP-Handshake" || bad "MCP antwortet nicht"

sched=$(curl -s -m 30 -X POST "https://runtime.codewords.ai/run/schedule_runs/list" -H "$AUTH" \
        -H 'Content-Type: application/json' -d '{}' | python3 -c '
import sys, json
data = json.load(sys.stdin)
items = data.get("schedules") or []
print(sum(1 for s in items if s.get("serviceName") == "Ilvana Airtable MCP" and s.get("active")))
')
[ "$sched" -ge 2 ] && ok "$sched aktive Zeitpläne (Zeitumstellung + Tageslauf)" || bad "nur $sched aktive Zeitpläne"

nh=$(curl -s -m 30 -H "$AUTH" "$NOTION/health")
printf '%s' "$nh" | grep -q '"status": *"ok"' && ok "Notion-Sync erreichbar" || bad "Notion-Sync antwortet nicht"

echo
[ "$fail" -eq 0 ] && echo "STACK OK" || echo "$fail Punkt(e) auffällig"
exit $fail
