#!/usr/bin/env bash
# REST-Helfer: ./scripts/ilvana.sh <werkzeug> '<json>'
set -euo pipefail

: "${CODEWORDS_API_KEY:?CODEWORDS_API_KEY fehlt}"
BASE="${ILVANA_URL:-https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7}"
TOOL="${1:?Werkzeugname fehlt, z.B. candidates_search}"
BODY="${2:-{}}"

curl -s -X POST "$BASE/tools/$TOOL" \
  -H "Authorization: Bearer $CODEWORDS_API_KEY" \
  -H "X-Actor: ${ILVANA_ACTOR:-cli}" \
  -H 'Content-Type: application/json' \
  -d "$BODY" | python3 -m json.tool
