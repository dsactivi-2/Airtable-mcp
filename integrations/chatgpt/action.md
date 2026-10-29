# ChatGPT — Action einrichten

1. GPT erstellen → **Configure** → **Actions** → *Create new action*
2. **Schema importieren:** *Import from URL* → `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json`
   (Fallback: Inhalt von `openapi/ilvana-airtable.openapi.json` einfügen)
3. **Authentication:** *API Key* → Auth Type **Bearer** → Wert = CodeWords-Key
4. **Instructions:** Inhalt von `integrations/chatgpt/instructions.md` einfügen (oder `skills/ilvana-airtable/SKILL.md`)
5. **Knowledge:** `skills/ilvana-airtable/references/schema.md`, `filtering.md`, `tags.md` hochladen
6. Testen: „Wer ist Haris Mihaljevic und was ist der nächste Schritt?"

## Grenzen

- Der Dienst hat **31** Operationen, ChatGPT erlaubt **30**: beim Import eine weglassen (z. B. `schedule_sync`) oder eine zweite Action anlegen.
- Keine Binärdaten: `document_upload` braucht eine Datei-Adresse (`file`), keinen Chat-Upload.
- Kein Streaming; 6–12 Sekunden pro Aufruf (Airtable-Abfrage).
- Der Key steckt in der Action-Konfiguration, nie im Prompt.
