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


## Protokoll, Fehler und Alarme

| Werkzeug | Zweck |
|---|---|
| `audit_list` | Verlauf: welcher Aufrufer hat wann welches Werkzeug auf welchem Datensatz ausgeführt |
| `error_log` | fehlgeschlagene Aufrufe mit Ursache und Status |
| `alerts_list` | gespeicherte Alarme inkl. Hinweis, ob ein Alarm-Webhook konfiguriert ist |
| `data_health` | Qualitätsprüfung: ohne Status, ohne nächste Aktion, überfällig, fehlende Unterlagen, verpasste Termine, doppelte Telefonnummern |

Aufrufer (`actor`) kommt aus dem Header `X-Actor` bzw. `X-Client`; ohne Header nutzt der Dienst die Aufrufer-ID der Plattform.

`ALERT_WEBHOOK_URL` (optional): Ist die Variable gesetzt, schickt der Dienst bei Fehlern und Datenauffälligkeiten ein JSON an diese Adresse — die eigene Plattform verteilt es auf Mail, Viber, Messenger oder SMS. Ohne die Variable werden Alarme nur gespeichert.

## Airtable Automation

`POST /hooks/airtable` — eine Airtable-Automation meldet eine Änderung, der Dienst reagiert sofort statt beim nächsten Tageslauf:

```json
{"record_id": "rec...", "mode": "apply", "event": "Status gewechselt"}
```

Ist `HOOK_SECRET` gesetzt, muss `hook_secret` im JSON-Body stehen (Header werden entfernt).

## Einrichtung

Vollständige Anleitung inklusive der drei Variablen (`AIRTABLE_PAT`, `HOOK_SECRET`, `ALERT_WEBHOOK_URL`),
Agenten-Verbindung und Airtable-Automation: [docs/setup-und-nutzung.md](docs/setup-und-nutzung.md)


## Konfiguration und Base-Änderungen über den Agenten

| Werkzeug | Zweck |
|---|---|
| `hook_test` | Airtable-Hook testen: URL, Header, Beispiel-Body und geplante Aktionen — ohne zu schreiben |
| `config_get` / `config_set` | Alarm-Webhook, Hook-Secret und Standard-Base setzen; wirkt sofort |
| `table_create`, `field_create`, `field_update` | Base-Struktur erweitern — standardmäßig als Vorschau, echt nur mit `confirm=true` |

Details: [references/config-and-hooks.md](skills/ilvana-airtable/references/config-and-hooks.md)


## Für Kollegen im Büro

- Korisničko uputstvo (bosanski): [docs/nutzeranleitung-bs.md](docs/nutzeranleitung-bs.md)
- Prompt za AI video uputstvo: [docs/video-prompt.md](docs/video-prompt.md)


## Werkzeuge (30)

**Lesen (9)** — `schema_get`, `candidates_search`, `applications_search`, `candidate_dossier`,
`application_get`, `documents_list`, `casting_ratings_list`, `pipeline_summary`, `due_report`

**Schreiben (7)** — `application_create`, `application_update`, `applications_bulk_update`, `application_add_note`,
`casting_rating_upsert`, `document_upload`, `tasks_manage`

**Automatik (3)** — `automation_rules`, `automation_run`, `automation_log`

**Betrieb (8)** — `audit_list`, `error_log`, `alerts_list`, `data_health`, `hook_test`,
`config_get`, `config_set`, `service_info`

**Struktur (3)** — `table_create`, `field_create`, `field_update`

## Projektstruktur

```
ilvana_airtable_mcp.py          der Dienst (FastAPI + FastMCP, PEP 723)
openapi/                        Action-Definition für ChatGPT und Grok
skills/                         Agenten-Wissen, pro Framework eine Datei
docs/                           Einrichtung, Verbindung, Schema, Uputstvo, Video-Prompt
scripts/smoke.sh                Smoke-Test gegen den laufenden Dienst
.github/workflows/ci.yml        Syntax, Abhängigkeiten, Werkzeugzahl, STEPLOG, Secret-Scan
```

## Qualitätschecks

| Prüfung | wo |
|---|---|
| Syntax und Abhängigkeiten | CI |
| Werkzeugzahl = OpenAPI-Operationen | CI |
| STEPLOG je Werkzeug | CI |
| keine Schlüssel im Repo | CI |
| laufender Dienst (health, 28 Werkzeuge, Lesetest) | `scripts/smoke.sh` |
| Verhalten aller Werkzeuge | siehe `CHANGELOG.md` und `docs/setup-und-nutzung.md` |
