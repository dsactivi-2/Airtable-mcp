# Codex

```bash
git clone https://github.com/dsactivi-2/Airtable-mcp.git
cd Airtable-mcp
export CODEWORDS_API_KEY="<key>"
export ILVANA_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
export ILVANA_ACTOR="codex"
```

- `AGENTS.md` im Repo wird automatisch gelesen.
- MCP: `integrations/codex/mcp.json` übernehmen.
- REST: `./scripts/ilvana.sh <werkzeug> '<json>'`

```bash
./scripts/ilvana.sh candidates_search '{"query":"Mihaljevic","limit":5}'
./scripts/ilvana.sh candidate_dossier  '{"record_id":"recuQxflPVccPo9xT"}'
./scripts/ilvana.sh data_health        '{}'
./scripts/ilvana.sh audit_list         '{"limit":10,"actor":"codex"}'
```
