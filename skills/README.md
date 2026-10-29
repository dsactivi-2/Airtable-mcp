# Skills — Ilvana Airtable

Ein Dienst, 31 Werkzeuge, vier Agenten-Frameworks. Jeder Agent bekommt **eine** Kerndatei und **eine**
Framework-Datei.

| Framework | Skill | Anbindung | Setup-Prompt |
|---|---|---|---|
| Hermes Agent | [frameworks/hermes/SKILL.md](frameworks/hermes/SKILL.md) | MCP (Streamable HTTP) | [../integrations/hermes/SETUP-PROMPT.md](../integrations/hermes/SETUP-PROMPT.md) |
| Codex | [frameworks/codex/SKILL.md](frameworks/codex/SKILL.md) | MCP oder REST + `AGENTS.md` | [../integrations/codex/SETUP-PROMPT.md](../integrations/codex/SETUP-PROMPT.md) |
| ChatGPT (Web) | [frameworks/chatgpt/SKILL.md](frameworks/chatgpt/SKILL.md) | Action über OpenAPI | [../integrations/chatgpt/SETUP-PROMPT.md](../integrations/chatgpt/SETUP-PROMPT.md) |
| Grok (Web) | [frameworks/grok/SKILL.md](frameworks/grok/SKILL.md) | Custom Action oder Funktionskatalog | [../integrations/grok/SETUP-PROMPT.md](../integrations/grok/SETUP-PROMPT.md) |

Gemeinsame Grundlage für alle: [ilvana-airtable/SKILL.md](ilvana-airtable/SKILL.md) mit den Referenzen

- `references/schema.md` — Felder, Typen, Auswahlwerte, schreibbar ja/nein
- `references/filtering.md` — Suche und Filter mit JSON
- `references/tags.md` — Tag-System und was Airtable automatisch berechnet
- `references/automation.md` — Regeln, Tageslauf, Protokoll
- `references/writing.md` — Anlegen, Ändern, Uploads, Dubletten
- `references/config-and-hooks.md` — Konfiguration über den Agenten, Hook-Test, Base-Änderungen
- `references/good-to-have.md` — offene Verbesserungen
