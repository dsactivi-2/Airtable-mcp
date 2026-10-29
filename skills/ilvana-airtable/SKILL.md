---
name: ilvana-airtable
description: Kandidaten-CRM der Ilvana i Hase GbR in Airtable. Lesen, suchen, filtern, schreiben, Dokumente hochladen und Automatik steuern — über MCP oder JSON-HTTP.
---

# Ilvana Airtable — Skill

Dieses Skill macht einen Agenten produktiv mit der Bewerber-Datenbank. Es beschreibt **was** drin ist,
**wie** gefiltert wird, **welche Tags** wann gesetzt werden, was Airtable **automatisch** berechnet und
was der Agent selbst tun muss.

## Wofür

Bewerbungsprozess für Arbeitskräfte aus dem Westbalkan nach Deutschland: Bewerbung → Casting → Vertrag →
Predsaglasnost → Visum → Arbeitsbeginn. Zwei Bases mit identischem Aufbau:

- `kopieren` — **Standard**, Arbeitsbase (108 Bewerbungen)
- `original` — Produktionsbase (100 Bewerbungen), nur auf ausdrückliche Anweisung beschreiben

## Verbindung

Der Dienst heißt **Ilvana Airtable MCP** (`ilvana_airtable_mcp_8b158ec7`).

| Client | Weg |
|---|---|
| Hermes Agent (MCP) | MCP-Endpunkt des Dienstes unter `/mcp/`, Header `Authorization: Bearer <CODEWORDS_API_KEY>` |
| Codex / CLI | `POST <Dienst-URL>/tools/<werkzeug>` mit JSON-Body |
| ChatGPT / Grok (web) | REST-Endpunkte als Action; Werkzeugdefinitionen unter `GET /schema/tools` (OpenAI-Format) |
| n8n / eigene App | dieselben JSON-Endpunkte |

Wichtig: `GET /schema/tools` liefert die vollständigen Funktionsdefinitionen. Arbeite **immer** damit,
statt Parameter zu raten.

## Goldene Regeln

1. **Erst lesen, dann schreiben.** Vor jeder Änderung `candidate_dossier` oder `applications_search` aufrufen.
2. **Nie Feldnamen raten.** Nicht schreibbare Felder (Formeln, Verknüpfungen, Anhänge) lehnt der Dienst mit
   einer Liste der erlaubten Felder ab. Siehe `references/schema.md`.
3. **Auswahlwerte exakt treffen.** `Počeo sa radom ` enthält ein Leerzeichen am Ende; `ODBIJEN` ist Großschreibung.
4. **Notizen anhängen, nicht überschreiben** — dafür `application_add_note` nutzen.
5. **Massenänderung nur mit Vorschau:** `dry_run=true` (Standard) prüfen, dann `dry_run=false` **und** `confirm=true`. Max. 50 Datensätze.
6. **Original-Base nur nennen, wenn der Nutzer sie ausdrücklich will** (`base=original`).
7. **Nichts löschen.** Der Dienst kennt kein Löschen — das ist Absicht.
8. **Unsicherheiten benennen**, nicht glattbügeln: fehlende Unterlagen, doppelte Telefonnummern, unklare Status.

## Die vier Kernwerkzeuge

```json
// Wer ist das? Name, Handy, Festnetz, Kundennummer, Passnummer
POST /tools/candidates_search
{"query": "Mihaljevic", "phone": "+387 61 614 368", "limit": 10}
```

```json
// Komplette Akte als ein JSON — der Vorab-Abruf vor einem Anruf
POST /tools/candidate_dossier
{"record_id": "recuQxflPVccPo9xT"}
```

```json
// Filter nach Status, Terminen, Fristen, fehlenden Unterlagen
POST /tools/applications_search
{"status_kandidata": "Casting", "only_overdue": true, "limit": 25}
```

```json
// Schreiben mit Protokoll-Notiz
POST /tools/application_update
{"record_id": "rec...", "fields": {"Status kandidata": "Primljeni"}, "note": "Casting bestanden"}
```

## Wohin gehört welches Wissen

| Thema | Datei |
|---|---|
| Alle Tabellen, Felder, Typen, Auswahlwerte, schreibbar ja/nein | `references/schema.md` |
| Jeder Filter, jede Suche, Paginierung, Massenänderung | `references/filtering.md` |
| Tag-System: welches Tag gehört zu welcher Prozessstufe, wann setzen, wann entfernen | `references/tags.md` |
| Automatik: Regeln, Tagesbericht, Doppel-Auslöser, Protokoll | `references/automation.md` |
| Was fehlt noch, was wäre sinnvoll | `references/good-to-have.md` |

## Antwortstil

Antworte in der Sprache des Nutzers (meist Deutsch), mit Klarnamen statt Record-IDs. Bei Listen: Name,
Status, nächste Aktion, Frist — keine Feld-Wüsten. Immer sagen, **was** geändert wurde und **wo**.
