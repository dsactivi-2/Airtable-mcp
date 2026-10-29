---
name: ilvana-airtable-grok
description: Ilvana-Airtable für Grok im Web — kein MCP-Connector, Wege über Custom Action oder Funktionskatalog, Grenzen und Prompt-Bausteine.
---

# Grok (Web) — Ilvana Airtable

Grok hat **keinen** MCP-Connector. Zwei Wege funktionieren:

## Weg A — Custom Action (wenn verfügbar)

Identisch zu ChatGPT:

1. Aktion anlegen, `openapi/ilvana-airtable.openapi.json` importieren
2. Auth: **Bearer** mit `CODEWORDS_API_KEY`
3. Server-URL steht bereits im Schema

## Weg B — Funktionskatalog ohne Connector

1. `GET https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/schema/tools` abrufen
2. Die `tools`-Liste in den Funktionskatalog deiner Vermittlung laden
3. Aufrufe über deine Vermittlung senden, die Basis-URL und Key serverseitig hält

Wichtig: **Key niemals im Prompt** — nur in der Konfiguration der Vermittlung.

## Was man Grok in den Prompt gibt

```
Du hast Zugriff auf das Kandidaten-CRM der Ilvana i Hase (28 Funktionen).
Feldnamen stehen in der angehängten Schema-Referenz. Auswahlwerte exakt treffen.
Vor Änderungen lesen und bestätigen lassen. Massenänderungen nur als Vorschau.
Keine Löschungen. Antworten auf Deutsch, Namen statt IDs.
```

Wenn `references/schema.md`, `filtering.md` und `tags.md` als Wissensdateien mitgegeben werden, kann Grok
auch ohne Werkzeuge korrekt beraten — dann führt ein Mensch die Aufrufe aus.

## Grenzen

- Kein MCP, kein Streaming, keine Datei-Uploads aus dem Chat
- Laufzeit 6–10 Sekunden pro Aufruf
- Ohne Connector keine automatische Werkzeugerkennung — die Funktionsliste muss mit
