# Verbindung mit den Agenten

Der Dienst ist **einmal** deployed und wird von allen Agenten geteilt. Er hält den Airtable-Schlüssel —
kein Agent braucht direkten Airtable-Zugang.

## Was du brauchst

| Ding | Woher | Wofür |
|---|---|---|
| **Basis-URL** | `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7` | alle Aufrufe |
| **MCP-Endpunkt** | `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/` | Hermes, Codex, alles mit MCP |
| **CodeWords API Key** | codewords.agemo.ai → Einstellungen → API-Keys | Authentifizierung (`Authorization: Bearer …`) |
| **Airtable-Token** | liegt bereits im Dienst | **nicht** an Agenten weitergeben |

Der API-Key ist das einzige Geheimnis, das ein Agent bekommt. Er gilt für dein CodeWords-Konto — behandle
ihn wie ein Passwort. Wenn ein Agent kompromittiert wird: Key erneuern, alle Agenten aktualisieren.

## Kurztest ohne Agent

```bash
curl -H "Authorization: Bearer $CODEWORDS_API_KEY" \
  https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/health
```

Erwartet: `{"status":"ok","tools":18,...}`

## Hermes Agent (MCP)

Hermes spricht MCP über Streamable HTTP. Konfiguration:

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": { "Authorization": "Bearer <CODEWORDS_API_KEY>" }
    }
  }
}
```

Danach stehen 30 Werkzeuge bereit (`schema_get`, `candidates_search`, `applications_search`,
`candidate_dossier`, `application_update`, `document_upload`, `automation_run`, …).
Lade zusätzlich `skills/ilvana-airtable/SKILL.md` als System- oder Projektwissen.

## Codex

Zwei Wege, beide gültig:

1. **MCP** — dieselbe Konfiguration wie bei Hermes, im MCP-Abschnitt der Codex-Konfiguration.
2. **REST + Repo-Wissen** — Codex liest `AGENTS.md` aus dem Repo automatisch. Ergänze die Umgebung:

```bash
export ILVANA_AIRTABLE_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
export CODEWORDS_API_KEY="<key>"

curl -X POST "$ILVANA_AIRTABLE_URL/tools/candidates_search" \
  -H "Authorization: Bearer $CODEWORDS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"Mihaljevic","limit":5}'
```

## ChatGPT (Web, eigener GPT)

ChatGPT spricht kein MCP. Nutze eine **Action**:

1. GPT erstellen → *Configure* → *Actions* → *Create new action*
2. **Schema importieren:** URL `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json` angeben (oder Inhalt von `openapi/ilvana-airtable.openapi.json` einfügen)
3. **Authentication:** *API Key* → Auth Type **Bearer** → Key = CodeWords API Key
4. **Instructions:** Inhalt von `skills/ilvana-airtable/SKILL.md` einfügen (die Referenzdateien als
   Wissensdateien hochladen)
5. Testen: „Wer ist Haris Mihaljevic und was ist der nächste Schritt?“

Die Action enthält 30 Operationen — genau am ChatGPT-Limit von 30. Für mehr Werkzeuge eine zweite Action anlegen.

## Grok (Web)

Grok hat keinen MCP-Connector. Zwei praktikable Wege:

1. **Custom Action / Connector**, falls verfügbar: `openapi/ilvana-airtable.openapi.json` importieren,
   Bearer-Auth mit dem CodeWords API Key — identisch zu ChatGPT.
2. **Ohne Connector:** Werkzeugdefinitionen aus
   `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/schema/tools` (OpenAI-Format)
   in den Funktionskatalog laden und die Aufrufe über deine eigene Vermittlung senden. Der Agent braucht
   dann die Basis-URL und den Key als Server-Konfiguration, nicht im Prompt.

Wichtig: **keinen** Schlüssel in den Chat-Prompt schreiben — nur in die Konfiguration/Umgebung.

## Rechte pro Agent begrenzen

Der Dienst kennt heute eine Ebene (alles oder nichts). Wenn du Agenten unterschiedlich berechtigen willst:
`applications_bulk_update` und `document_upload` sind die riskanten Werkzeuge — bei einem reinen Lese-Agenten
im Prompt ausschließen („nutze nur search/dossier/summary“) oder eine zweite Instanz mit reduziertem
Werkzeugsatz deployen.

## Fehlersuche

| Symptom | Ursache |
|---|---|
| `401` / `Authentication required` | Key fehlt, abgelaufen oder falscher Header (`Authorization: Bearer …`) |
| `406 Not Acceptable` bei `/mcp/` | Client sendet nicht `Accept: application/json, text/event-stream` — MCP-Client nutzen, nicht curl |
| `Kein Zugriff auf diese Airtable-Base` | Base fehlt im Airtable-Token unter Access (betrifft `original`) |
| `Unbekanntes Werkzeug` | Name falsch — Liste über `/schema/tools` |
