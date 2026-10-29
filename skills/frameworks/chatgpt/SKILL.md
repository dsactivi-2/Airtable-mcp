---
name: ilvana-airtable-chatgpt
description: Ilvana-Airtable als Custom-GPT-Action — Schema importieren, Bearer-Auth, Grenzen von Actions, Prompt-Bausteine.
---

# ChatGPT (Web, eigener GPT) — Ilvana Airtable

ChatGPT spricht kein MCP. Der Weg ist eine **Action** über OpenAPI.

## Einrichten

1. GPT erstellen → **Configure** → **Actions** → **Create new action**
2. **Schema:** URL `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json` importieren (30 Operationen — genau am Limit); alternativ die Datei `openapi/ilvana-airtable.openapi.json` einfügen
3. **Authentication:** *API Key* → Auth Type **Bearer** → Key = `CODEWORDS_API_KEY`
4. **Instructions:** Inhalt von `skills/ilvana-airtable/SKILL.md`
5. **Knowledge:** die Dateien aus `references/` hochladen (Schema, Filter, Tags, Automatik)

## Grenzen von Actions — wichtig

- **Keine Binärdaten:** `document_upload` braucht eine öffentlich erreichbare Datei-Adresse
  (`file`), keine Uploads aus dem Chat. Für echte Uploads Hermes oder Codex nutzen.
- **Kein Streaming:** Antworten kommen als JSON, Laufzeit 6–10 Sekunden pro Aufruf.
- **Kein Zustand:** jede Aktion ist ein Einzelaufruf; für mehrstufige Aufgaben die Instructions nutzen.
- **Kein Secret im Prompt** — der Key steckt in der Action-Konfiguration.

## Prompt-Bausteine für die Instructions

```
Du arbeitest mit dem Kandidaten-CRM der Ilvana i Hase.
Vor jeder Änderung: candidate_dossier lesen und die Absicht bestätigen lassen.
Nutze nur Felder aus references/schema.md. Auswahlwerte exakt übernehmen.
Massenänderungen immer erst als Vorschau (dry_run=true) zeigen.
Keine Löschvorgänge. Bei Unklarheit nachfragen.
Antworte auf Deutsch, mit Namen statt Record-IDs.
```

## Typische Aktionen

| Frage des Nutzers | Operation |
|---|---|
| „Wer ist Haris Mihaljevic?" | `candidates_search` → `candidate_dossier` |
| „Was ist überfällig?" | `applications_search` mit `only_overdue` |
| „Wie viele sind in welcher Stufe?" | `pipeline_summary` |
| „Trag eine Notiz ein" | `application_add_note` |
| „Prüf die Datenqualität" | `data_health` |
| „Was ist zuletzt passiert?" | `audit_list` |
