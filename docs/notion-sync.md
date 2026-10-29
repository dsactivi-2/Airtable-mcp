# Notion-Sync

Zweiter Dienst im Stack: `Ilvana Notion Sync` (`ilvana_notion_sync_0468633e`).
Er liest die Werkzeugschemata vom Ilvana-MCP und spiegelt sie als Notion-Datenbank.

## Warum

Die 31 Werkzeuge sind die Schnittstelle für Agenten. Im Repo stehen sie als Markdown, im Dienst als JSON.
Notion ist der Ort, an dem das Team sie ohne Terminal lesen, kommentieren und verlinken kann.

## Ablauf

1. `GET {{ILVANA}}/schema/tools` — 31 Werkzeuge + `/health` für die Version
2. Notion: Datenbank **Ilvana Tools** unter der konfigurierten Seite suchen, sonst anlegen
3. Je Werkzeug: Seite anlegen oder aktualisieren — aber nur, wenn sich die Prüfsumme geändert hat

Datenbank: [4082cc93-a106-817a-907c-c61bf7ca8135](https://www.notion.so/4082cc93a106817a907cc61bf7ca8135)

## Eigenschaften je Seite

| Eigenschaft | Inhalt |
|---|---|
| Werkzeug | Name, z. B. `candidates_search` |
| Gruppe | Lesen · Schreiben · Automatik · Betrieb · Struktur |
| Beschreibung | Text aus der Funktionsdefinition |
| Parameter | jeder Parameter mit Typ, Pflicht/optional, Standardwert und Beschreibung |
| Pflichtfelder | kommaseparierte Liste |
| Prüfsumme | erkennt Änderungen, verhindert unnötige Schreibzugriffe |
| Stand | Zeitpunkt der letzten Aktualisierung |

## Endpunkte

| Methode | Pfad | Zweck |
|---|---|---|
| POST | `/` | Sync ausführen, Body `{"dry_run": false}` |
| POST | `/preview` | nur zählen, nichts schreiben |
| GET | `/health` | Status |

## Betrieb

- Zeitplan: `cron(0 4 * * ? *)` — täglich 04:00 UTC, nach dem Zeitplan-Abgleich (03:00) und vor dem Tageslauf (05:00/06:00)
- Erwartete Ausgabe bei unverändertem Dienst: `0 neu, 0 aktualisiert, 31 unverändert`
- Nach einem Deploy des Ilvana-Dienstes erkennt der nächste Lauf geänderte Beschreibungen und aktualisiert nur diese Seiten

## Einrichtung

Zwei Variablen, beide im Secret-Store:

| Variable | Woher |
|---|---|
| `NOTION_TOKEN` | notion.so → Einstellungen → Connections → *Develop or manage integrations* → New integration (Internal), Rechte: Read, Insert, Update content |
| `NOTION_PARENT_PAGE` | Link der Zielseite — diese Seite muss mit der Integration geteilt sein (Seite → ••• → Connections) |

Zielseite ändern: `NOTION_PARENT_PAGE` überschreiben, dann einmal `POST /` — die Datenbank wird am neuen Ort angelegt.

## Fehlerbilder

| Meldung | Ursache |
|---|---|
| `Objekt nicht gefunden. Ist die Zielseite mit der Integration geteilt?` | Seite nicht freigegeben oder falsche ID |
| `NOTION_TOKEN ist nicht gesetzt` | Secret fehlt im Dienst |
| `schema/tools antwortet mit 401` | CodeWords-Key im Dienst ungültig |
| `0 Werkzeuge` | Ilvana-Dienst nicht erreichbar oder Werkzeugliste leer |
