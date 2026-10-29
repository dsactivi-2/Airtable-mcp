# Grok (Web) — Action einrichten

Grok hat keinen MCP-Connector. Zwei Wege:

## A — Custom Action (wenn verfügbar)

Identisch zu ChatGPT: Spec-URL `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json` importieren, Auth **Bearer** mit CodeWords-Key.

## B — Funktionskatalog ohne Connector

1. `GET https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/schema/tools` abrufen (Bearer nötig)
2. `tools`-Liste in den Funktionskatalog der Vermittlung laden
3. Aufrufe über die Vermittlung senden, die URL und Key serverseitig hält

## Prompt-Baustein

```
Du hast Zugriff auf das Kandidaten-CRM der Ilvana i Hase (31 Funktionen).
Feldnamen stehen in der beigefügten Schema-Referenz, Auswahlwerte exakt treffen.
Vor Änderungen lesen und bestätigen lassen, Massenänderungen nur als Vorschau.
Keine Löschungen. Antworten auf Deutsch, Namen statt IDs.
```

Grenzen wie bei ChatGPT: keine Datei-Uploads aus dem Chat, kein Streaming.
