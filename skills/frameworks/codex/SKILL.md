---
name: ilvana-airtable-codex
description: Codex-Anbindung an das Ilvana-Airtable-MCP — AGENTS.md, MCP-Block oder REST mit curl, Umgebungsvariablen, Arbeitsweise.
---

# Codex — Ilvana Airtable

Codex liest `AGENTS.md` aus dem Repo automatisch. Damit ist das Grundwissen ohne Konfiguration da.

## Variante A — MCP

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": { "Authorization": "Bearer <CODEWORDS_API_KEY>", "X-Actor": "codex" }
    }
  }
}
```

## Variante B — REST im Terminal

```bash
export ILVANA_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
export CODEWORDS_API_KEY="<key>"

ilvana() { curl -s -X POST "$ILVANA_URL/tools/$1"   -H "Authorization: Bearer $CODEWORDS_API_KEY"   -H "X-Actor: codex" -H "Content-Type: application/json" -d "${2:-{}}"; }

ilvana candidates_search '{"query":"Mihaljevic","limit":5}'
ilvana candidate_dossier  '{"record_id":"recPxflPVccPo9xT"}'
ilvana data_health        '{}'
```

## Arbeitsweise

1. `schema_get` einmal am Anfang, dann Feldnamen aus `references/schema.md` verwenden.
2. Schreiben nur auf freigegebene Felder; Fehlermeldung nennt die erlaubten.
3. Massenänderung: erst `dry_run=true`, Diff zeigen, dann `confirm=true` — nie in einem Schritt.
4. Struktur-Änderungen: `preview` ist Standard; niemals `preview=false` ohne Zustimmung.
5. Kein Secret im Code oder in Commits — nur Umgebungsvariablen.

## Nützlich beim Entwickeln

```bash
ilvana config_get '{}'
ilvana hook_test '{}'
ilvana audit_list '{"limit":10,"actor":"codex"}'
ilvana error_log '{"limit":5}'
```
