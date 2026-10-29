---
name: ilvana-airtable-hermes
description: Hermes-Agent-Anbindung an das Ilvana-Airtable-MCP — Konfiguration, Werkzeugnutzung, Actor-Kennzeichnung, Grenzen.
---

# Hermes Agent — Ilvana Airtable

Hermes spricht MCP über Streamable HTTP. Kein eigener Server, kein lokaler Prozess.

## Einrichten

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": {
        "Authorization": "Bearer <CODEWORDS_API_KEY>",
        "X-Actor": "hermes"
      }
    }
  }
}
```

`X-Actor: hermes` sorgt dafür, dass im Verlauf (`audit_list`) steht, dass Hermes gehandelt hat.
Ohne Header protokolliert der Dienst die Aufrufer-ID der Plattform.

Danach `skills/ilvana-airtable/SKILL.md` + `references/` als Projektwissen laden.

## Werkzeuge

28 Werkzeuge in Gruppen: Lesen (9), Schreiben (6), Automatik (3), Betrieb (6), Struktur (3).
Hermes erkennt sie über `tools/list` selbst — keine manuelle Registrierung.

## Praktische Hinweise

- Antworten sind JSON mit `success` und `result`; Fehler kommen als `McpError` mit deutschem Text.
- Vor Massenänderungen `dry_run=true` nutzen und das Ergebnis dem Nutzer zeigen.
- `document_upload` erwartet eine Datei-Adresse (`file`) — Hermes kann Dateien aus seinem Kontext
  bereitstellen, Rohbytes nicht.
- Nach jeder Änderung kurz den Verlauf prüfen: `audit_list {"actor": "hermes"}`.

## Grenzen

- Kein Löschen über den Dienst
- `AIRTABLE_PAT` ist nicht über Werkzeuge änderbar
- Struktur-Änderungen brauchen `schema.bases:write` im Airtable-Token
