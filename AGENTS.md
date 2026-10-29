# AGENTS.md

Dieses Repository enthält den **Ilvana Airtable MCP**: einen Dienst, der die Bewerber-Datenbank
der Ilvana i Hase über MCP und über eine JSON-HTTP-API zugänglich macht.

## Für Agenten, die hier arbeiten

Bevor du Felder liest oder schreibst, lade das Skill:

```
skills/ilvana-airtable/SKILL.md
```

Es verweist auf:

- `references/schema.md` — alle Tabellen, Felder, Typen, Auswahlwerte, schreibbar ja/nein (aus Airtable erzeugt)
- `references/filtering.md` — jede Suche und jeder Filter mit JSON-Beispielen
- `references/tags.md` — welche Tags zu welcher Prozessstufe gehören, wann sie gesetzt werden, was Airtable automatisch berechnet
- `references/automation.md` — Regeln, Tagesbericht, Doppel-Auslöser, Protokoll
- `references/good-to-have.md` — offene Verbesserungen

## Kurzfassung der Regeln

1. Erst lesen (`candidate_dossier`), dann schreiben.
2. Nur schreibbare Felder setzen; Auswahlwerte exakt treffen.
3. Notizen anhängen, nie überschreiben.
4. Massenänderung: Vorschau, dann `dry_run=false` **und** `confirm=true`.
5. `base=kopieren` ist Standard; `original` nur auf ausdrückliche Anweisung.
6. Nichts löschen — der Dienst kann es nicht, und das bleibt so.

## Einstieg für Menschen

- Betrieb: CodeWords-Service `ilvana_airtable_mcp_8b158ec7`
- Quelle: `ilvana_airtable_mcp.py`
- Funktionsdefinitionen: `GET /schema/tools`
