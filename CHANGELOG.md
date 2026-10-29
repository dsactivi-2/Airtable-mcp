# Changelog

## Notion Sync 1.0.0 — 2026-10-29

- Neuer Dienst `Ilvana Notion Sync`: spiegelt die 31 Werkzeugschemata in die Notion-Datenbank
  „Ilvana Tools" — eine Seite pro Werkzeug, mit Gruppe, Beschreibung, Parametern und Prüfsumme
- Vorschau-Endpunkt und täglicher Abgleich (`cron(0 4 * * ? *)`); zweiter Lauf: 31 unverändert

## 1.5.5 — 2026-10-29

- `schedule_sync`: stellt den Tagesplan automatisch auf Sommerzeit (`cron(0 5 * * ? *)`) bzw. Winterzeit
  (`cron(0 6 * * ? *)`) um — idempotent, täglich um 03:00 UTC aufgerufen
- Zweiter Zeitplan dafür angelegt; Tagesplan bleibt damit ganzjährig bei 07:00 Ortszeit
- ChatGPT-Hinweis: 31 Operationen überschreiten das Limit von 30 — beim Import eine weglassen

## 1.5.4 — 2026-10-29

- `POST /automation/daily` nimmt `base` und `mode` als JSON-Body (Query-Parameter erreichen den Dienst über die Runtime nicht)
- Tageslauf auf **apply** umgestellt, täglich 06:00 UTC = 07:00 Ortszeit (Winterzeit); erster Lauf geprüft: Emrah Dzafic erhielt Frist 2026-10-31 und eine Aufgabe

## 1.5.3 — 2026-10-29

- Öffentliche Spec-URL dokumentiert (jsDelivr `@main`, Tag `v1.5.3`) für den Actions-Import

- `GET /openapi.json` liefert die vollständige Werkzeug-Spec (30 Operationen + `/health`),
  direkt importierbar bei ChatGPT-Actions und Grok

## 1.5.2 — 2026-10-29

- Alarme protokollieren die Zustellung: `delivered`, `delivery_status`, `delivery_error`
- `alerts_list` zeigt damit, ob der Empfänger den Alarm wirklich angenommen hat
- `ALERT_WEBHOOK_URL` gesetzt — Alarm getestet, HTTP 200

## 1.5.1 — 2026-10-29

- Hook-Secret wird als Feld `hook_secret` im JSON-Body erwartet (Gateway entfernt `X-Hook-Secret`)
- `hook_test` zeigt den Aufruf mit Secret im Body
- Neue `docs/secrets-checkliste.md`: Herkunft, Eintragung und Rotation aller drei Secrets

## 1.5.0 — 2026-10-29

- `service_info`: Version, Werkzeugliste, Änderungsverlauf und Secret-Zuständigkeiten
- Klar dokumentiert, wer `AIRTABLE_PAT`, `HOOK_SECRET` und `ALERT_WEBHOOK_URL` einträgt
- Update-Hinweis: Agenten merken sich `version` und laden bei Änderung das Skill neu

## 1.4.0 — 2026-10-29

- `application_create` — neue Bewerbung anlegen, mit Dubletten-Schutz auf Telefonnummer (409)
- Neue Referenz `references/writing.md` (Anlegen, Ändern, Massenänderung, Notizen, Bewertungen, Uploads)
- OpenAPI auf 29 Operationen, README und Skills angeglichen

## 1.3.0 — 2026-10-29

- Alle 51 fehlenden Parameterbeschreibungen ergänzt (Function Calling)
- `apply` über `/hooks/airtable` ohne gesetztes `HOOK_SECRET` wird mit 401 gesperrt
- Repo-Härtung: LICENSE, SECURITY.md, .gitignore, CI-Workflow, Smoke-Test, Changelog

## 1.2.0 — 2026-10-29

- `hook_test` und `POST /hooks/airtable/test` — Verbindungstest ohne Schreibzugriff
- `config_get` / `config_set` — Webhook, Hook-Secret und Standard-Base über den Agenten
- `table_create`, `field_create`, `field_update` — Base-Struktur mit Vorschau und Bestätigung
- Skills pro Framework (Hermes, Codex, ChatGPT, Grok) plus Index

## 1.1.0 — 2026-10-29

- `audit_list`, `error_log`, `alerts_list`, `data_health`
- Alarm-Webhook, Aufrufer-Protokoll (`X-Actor`), Airtable-Automation-Haken
- Tageslauf meldet Datenauffälligkeiten

## 1.0.0 — 2026-10-29

- Erste Version: 22 Werkzeuge für zwei Bases (Suche, Akte, Schreiben, Uploads, Automatik)
- MCP (Streamable HTTP) und JSON-HTTP-API aus einem Dienst
- Kandidatensuche über Name, Handy, Festnetz, Kundennummer, Passnummer
- Dokument-Uploads (PDF, JPG, PNG, DOC, DOCX), Massenänderung mit Vorschau
