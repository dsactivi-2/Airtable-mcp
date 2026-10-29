# Ilvana Airtable MCP

MCP-Server und JSON-API fuer die Airtable-Bases **Ilvana i Hase (Kopieren)** und **Ilvana i Hase**.
Ein Dienst, drei Zugaenge: MCP-Werkzeuge fuer KI-Assistenten (Claude, ChatGPT, n8n), dieselben
Funktionen als HTTP-Endpunkte fuer Function Calling, und eine eingebaute Automatik mit
Tagesbericht und Folgeaufgaben bei Statuswechsel.

## Funktionen

**Lesen**
- `schema_get` - Tabellen, Felder, Typen und erlaubte Auswahlwerte beider Bases
- `candidates_search` - Suche ueber Name, Handy-/Festnetznummer (normalisiert), Kundennummer, Passnummer
- `applications_search` - Filter nach Status, Casting-Gruppe/-Ausgang, Vertrag, Visum, Zeitraeumen, ueberfaelligen Aktionen und fehlenden Unterlagen
- `candidate_dossier` - komplette Kandidatenakte als ein JSON, inkl. Dokumente, Bewertungen, Aufgaben und einem fertigen Vorab-Text fuer einen Anruf
- `application_get`, `documents_list`, `casting_ratings_list`, `pipeline_summary`, `due_report`

**Schreiben**
- `application_update` - nur freigegebene Felder, serverseitig validiert
- `applications_bulk_update` - Massenaenderung mit Vorschau (`dry_run=true`), Schreiben nur mit `dry_run=false` und `confirm=true`, maximal 50 Datensaetze
- `application_add_note` - Notiz mit Zeitstempel und Verfasser anhaengen statt ueberschreiben
- `casting_rating_upsert` - Casting-Bewertung anlegen oder aktualisieren
- `document_upload` - PDF, JPG, JPEG, PNG, DOC, DOCX bis 10 MB in die Anhang-Felder
- `tasks_manage` - Aufgaben in Table 1 lesen, anlegen, Status setzen

**Automatik**
- `automation_rules` - Regeln ansehen oder aendern (Statuswechsel fuehrt zu Folgeaufgabe)
- `automation_run` - `preview` zeigt den Plan, `apply` schreibt Aenderungen, Aufgaben und Protokoll
- `automation_log` - Protokoll aller Automatik- und Massenaenderungen

## Endpunkte

| Methode | Pfad | Zweck |
|---|---|---|
| POST | `/` | Dienstinfo oder Direktaufruf mit tool und arguments |
| POST | `/tools/{name}` | Ein Werkzeug mit JSON-Body aufrufen |
| GET | `/schema/tools` | Function-Calling-Definitionen (OpenAI-Format) |
| GET | `/schema` | Schema als JSON |
| GET | `/schema/document` | Schema als Markdown |
| POST | `/automation/daily` | Tagesbericht und Automatik, Standard nur Vorschau |
| GET | `/health` | Status |
| - | `/mcp/` | MCP (Streamable HTTP) fuer KI-Clients |

Alle Ein- und Ausgaben sind reines JSON mit stabilen Feldnamen.

## Konfiguration

| Variable | Pflicht | Zweck |
|---|---|---|
| `AIRTABLE_PAT` | ja | Airtable Personal Access Token (pat...) |
| `CODEWORDS_API_KEY` | ja | Laufzeit-Schluessel der Plattform |
| `CODEWORDS_RUNTIME_URI` | ja | Adresse der CodeWords-Runtime |
| `PORT` | nein | Standard 8000 |
| `LOGLEVEL` | nein | Standard INFO |

### Airtable-Token anlegen

1. airtable.com - Konto - Developer hub - Personal access tokens - Create new token
2. Scopes: data.records:read, data.records:write, schema.bases:read
3. Unter Access beide Bases hinzufuegen: Ilvana i Hase und Ilvana i Hase (Kopieren)
4. Token kopieren und als AIRTABLE_PAT hinterlegen

Fehlt eine Base im Token, antwortet der Dienst mit einer klaren Fehlermeldung statt mit falschen Daten.

## Sicherheit und Grenzen

- Schreibzugriff nur auf freigegebene Felder; Formeln, Verknuepfungen und Anhaenge sind gesperrt
- Auswahlwerte werden gegen die echten Airtable-Optionen validiert
- Jeder Datensatz wird pro Automatik-Regel genau einmal veraendert (Marker mit 180 Tagen Laufzeit)
- Kein Loeschen von Datensaetzen oder Dateien, keine Massenbereinigung
- Zustellung von E-Mail, Viber, Messenger und SMS erfolgt in der aufrufenden Plattform; dieser Dienst liefert den fertigen Berichtstext

## Betrieb

Der Dienst laeuft als CodeWords-Service (FastAPI + FastMCP). Der Tageslauf ist als Vorschau registriert (taeglich 07:00 Europe/Sarajevo). Umschalten auf echtes Schreiben: mode=apply.

## Schema

Vollstaendige Feldreferenz: [docs/airtable-schema.md](docs/airtable-schema.md)
