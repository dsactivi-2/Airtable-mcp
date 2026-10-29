---
name: ilvana-airtable
description: Kandidaten-CRM der Ilvana i Hase in Airtable — lesen, suchen, filtern, schreiben, Dokumente hochladen, Automatik steuern, konfigurieren und die Base-Struktur erweitern. 28 Werkzeuge über MCP oder JSON-HTTP.
---

# Ilvana Airtable — Kern-Skill

Bewerbungsprozess Westbalkan → Deutschland: Bewerbung → Casting → Vertrag → Predsaglasnost → Visum →
Arbeitsbeginn. Zwei Bases, identischer Aufbau:

- `kopieren` — Standard (108 Bewerbungen)
- `original` — Produktion (100 Bewerbungen), nur auf ausdrückliche Anweisung

## Verbindung

| Ding | Wert |
|---|---|
| Basis-URL | `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7` |
| MCP | dieselbe URL + `/mcp/` |
| Auth | `Authorization: Bearer <CODEWORDS_API_KEY>` |
| Funktionsdefinitionen | `GET /schema/tools` (OpenAI-Format) |
| OpenAPI | `openapi/ilvana-airtable.openapi.json` im Repo |

Der Airtable-Schlüssel liegt im Dienst — kein Agent braucht ihn.

## Goldene Regeln

1. **Erst lesen, dann schreiben** (`candidate_dossier` vor jeder Änderung).
2. **Nie Feldnamen raten.** Nicht schreibbare Felder stehen in `references/schema.md`.
3. **Auswahlwerte exakt.** `Počeo sa radom ` hat ein Leerzeichen am Ende, `ODBIJEN` ist Großschreibung.
4. **Notizen anhängen**, nie überschreiben (`application_add_note`).
5. **Massenänderung:** `dry_run=true` prüfen, dann `dry_run=false` **und** `confirm=true`, max. 50.
6. **Struktur-Änderungen** (Tabelle/Feld) immer erst `preview=true`, dann `confirm=true`.
7. **Original-Base nur nennen**, wenn der Nutzer sie ausdrücklich will.
8. **Nichts löschen** — der Dienst kann es nicht, das bleibt so.
9. **Unsicherheit benennen** statt glätten: fehlende Unterlagen, doppelte Nummern, unklare Status.

## Werkzeuge in Gruppen

**Lesen (9)** — `schema_get`, `candidates_search`, `applications_search`, `candidate_dossier`,
`application_get`, `documents_list`, `casting_ratings_list`, `pipeline_summary`, `due_report`

**Schreiben (6)** — `application_update`, `applications_bulk_update`, `application_add_note`,
`casting_rating_upsert`, `document_upload`, `tasks_manage`

**Automatik (3)** — `automation_rules`, `automation_run`, `automation_log`

**Betrieb (6)** — `audit_list`, `error_log`, `alerts_list`, `data_health`, `hook_test`,
`config_get`/`config_set`

**Struktur (3)** — `table_create`, `field_create`, `field_update`

## Die vier Kernaufrufe

```json
POST /tools/candidates_search   {"query": "Mihaljevic", "phone": "+387 61 614 368"}
POST /tools/candidate_dossier    {"record_id": "recuQxflPVccPo9xT"}
POST /tools/applications_search  {"status_kandidata": "Casting", "only_overdue": true}
POST /tools/application_update   {"record_id": "rec…", "fields": {"Status kandidata": "Primljeni"}, "note": "bestanden"}
```

## Was der Agent selbst konfigurieren darf

- Alarm-Webhook und Hook-Secret (`config_set`) — wirkt sofort, kein Redeploy
- Standard-Base (`config_set default_base`)
- Automatik-Regeln (`automation_rules set`)
- Base-Struktur: Tabellen und Felder anlegen/ändern (mit Vorschau)

**Nicht** über den Agenten änderbar: `AIRTABLE_PAT` (nur Platform-Panel) und das Löschen von Daten.

## Referenzen

| Thema | Datei |
|---|---|
| Felder, Typen, Auswahlwerte | `references/schema.md` |
| Suche und Filter | `references/filtering.md` |
| Tags, Stufen, automatische Felder | `references/tags.md` |
| Automatik und Tageslauf | `references/automation.md` |
| Konfiguration, Hook-Test, Base-Änderungen | `references/config-and-hooks.md` |
| Verbesserungsvorschläge | `references/good-to-have.md` |

## Antwortstil

Sprache des Nutzers (meist Deutsch), Klarnamen statt Record-IDs, bei Listen: Name, Status, nächste
Aktion, Frist. Immer sagen, was geändert wurde und wo.
