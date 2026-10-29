# Changelog

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
