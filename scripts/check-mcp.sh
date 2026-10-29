#!/usr/bin/env bash
# Prüft den MCP-Endpunkt genau so, wie Hermes ihn anspricht.
#   CODEWORDS_API_KEY=... ./scripts/check-mcp.sh
set -uo pipefail

: "${CODEWORDS_API_KEY:?CODEWORDS_API_KEY fehlt}"
BASE="${ILVANA_URL:-https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7}"
URL="$BASE/mcp/"
HEAD=(-H "Authorization: Bearer $CODEWORDS_API_KEY" -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream')

echo "1) initialize"
init=$(curl -s -m 60 "${HEAD[@]}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check-mcp","version":"1"}}}' \
  "$URL")
printf '%s' "$init" | grep -q '"serverInfo"' || { echo "  FEHLER: keine Serverantwort"; exit 1; }
echo "  OK   Server antwortet"
printf '%s' "$init" | grep -q 'Ilvana Airtable MCP' && echo "  OK   Server: Ilvana Airtable MCP"

echo "2) tools/list"
list=$(curl -s -m 60 "${HEAD[@]}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' "$URL")
count=$(printf '%s' "$list" | python3 -c '
import sys, json
names = set()
for line in sys.stdin.read().splitlines():
    line = line.strip()
    if line.startswith("data:"):
        try:
            payload = json.loads(line[5:].strip())
            for tool in payload.get("result", {}).get("tools", []):
                names.add(tool["name"])
        except Exception:
            pass
print(len(names))
')
echo "  Werkzeuge: $count"
[ "$count" -ge 30 ] || { echo "  FEHLER: zu wenige Werkzeuge"; exit 1; }
echo "  OK   mindestens 30 Werkzeuge"

echo
echo "MCP-Verbindung steht. Konfiguration für Hermes:"
echo "  URL:  $URL"
echo "  Authorization: Bearer <CODEWORDS_API_KEY>"
echo "  X-Actor: hermes"
