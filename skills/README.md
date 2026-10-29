# Skills — Ilvana Airtable

Ein Dienst, 29 Werkzeuge, vier Agenten-Frameworks. Jeder Agent bekommt **eine** Kerndatei und **eine**
Framework-Datei.

| Framework | Datei | Verbindungsweg |
|---|---|---|
| Hermes Agent | [frameworks/hermes/SKILL.md](frameworks/hermes/SKILL.md) | MCP (Streamable HTTP) |
| Codex | [frameworks/codex/SKILL.md](frameworks/codex/SKILL.md) | MCP oder REST + `AGENTS.md` |
| ChatGPT (Web, eigener GPT) | [frameworks/chatgpt/SKILL.md](frameworks/chatgpt/SKILL.md) | Action über OpenAPI |
| Grok (Web) | [frameworks/grok/SKILL.md](frameworks/grok/SKILL.md) | Custom Action oder Funktionskatalog |

Gemeinsame Grundlage für alle: [ilvana-airtable/SKILL.md](ilvana-airtable/SKILL.md) mit den Referenzen

- `references/schema.md` — Felder, Typen, Auswahlwerte, schreibbar ja/nein
- `references/filtering.md` — Suche und Filter mit JSON
- `references/tags.md` — Tag-System und was Airtable automatisch berechnet
- `references/automation.md` — Regeln, Tageslauf, Protokoll
- `references/writing.md` — Anlegen, Ändern, Uploads, Dubletten
- `references/config-and-hooks.md` — Konfiguration über den Agenten, Hook-Test, Base-Änderungen
- `references/good-to-have.md` — offene Verbesserungen
