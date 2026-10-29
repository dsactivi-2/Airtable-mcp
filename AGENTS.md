# AGENTS.md

Dieses Repository enthält den **Ilvana Airtable MCP**: einen Dienst, der die Bewerber-Datenbank
der Ilvana i Hase über MCP und über eine JSON-HTTP-API zugänglich macht — inklusive Automatik,
Protokoll, Konfiguration und Base-Änderungen.

## Für Agenten

Lies zuerst:

```
skills/README.md          → welches Skill für welches Framework
skills/ilvana-airtable/SKILL.md   → gemeinsame Grundlage, 28 Werkzeuge
```

Framework-spezifisch:

- Hermes Agent → `skills/frameworks/hermes/SKILL.md`
- Codex → `skills/frameworks/codex/SKILL.md`
- ChatGPT (Web) → `skills/frameworks/chatgpt/SKILL.md`
- Grok (Web) → `skills/frameworks/grok/SKILL.md`

## Beim Start

1. `POST /tools/service_info` — Version merken, `secrets` prüfen, `tool_names` lesen.
2. Ist die Version neuer als gemerkt: `changelog` lesen und dieses Skill neu laden.

## Kurzfassung

1. Erst lesen (`candidate_dossier`), dann schreiben.
2. Nur schreibbare Felder, Auswahlwerte exakt.
3. Notizen anhängen, nie überschreiben.
4. Massenänderung: Vorschau, dann `dry_run=false` **und** `confirm=true`.
5. Struktur-Änderungen: erst `preview=true`, dann `confirm=true`.
6. `base=kopieren` ist Standard; `original` nur auf Anweisung.
7. Nichts löschen — der Dienst kann es nicht.

## Für Menschen

- Betrieb: CodeWords-Service `ilvana_airtable_mcp_8b158ec7`
- Einrichtung: `docs/setup-und-nutzung.md`
- Verbindung je Agent: `docs/verbindung-agenten.md`
- Quelle: `ilvana_airtable_mcp.py`
