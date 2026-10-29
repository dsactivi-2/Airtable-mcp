# Hermes Agent — MCP anbinden

## 1. Konfiguration einsetzen

`mcp.json` aus diesem Ordner in die MCP-Konfiguration von Hermes übernehmen und
`REPLACE_WITH_CODEWORDS_API_KEY` durch deinen CodeWords-Key ersetzen:

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": {
        "Authorization": "Bearer REPLACE_WITH_CODEWORDS_API_KEY",
        "X-Actor": "hermes"
      }
    }
  }
}
```

Den Key findest du unter codewords.agemo.ai → Einstellungen → API-Keys.

## 2. Vorher prüfen, ob der Endpunkt steht

```bash
export CODEWORDS_API_KEY="<key>"
./scripts/check-mcp.sh
```

Erwartet: Serverantwort, 31 Werkzeuge, am Ende die Konfigurationszeilen.
Das Skript spricht denselben Weg an wie Hermes (Streamable HTTP, `Accept: application/json, text/event-stream`).

## 3. Wissen laden

`skills/ilvana-airtable/SKILL.md` plus `references/` als Projekt- oder Systemwissen hinterlegen.
Sonst kennt der Agent die Werkzeuge, aber nicht die Feldnamen und Tag-Regeln.

## 4. Erster Test im Chat

„Wer ist Haris Mihaljevic und was ist der nächste Schritt?"

Erwartet: Hermes ruft `candidates_search` bzw. `candidate_dossier` auf und antwortet mit Name, Status,
nächster Aktion und Frist.

## 5. Nachweis, dass Hermes gehandelt hat

```bash
./scripts/ilvana.sh audit_list '{"limit":5,"actor":"hermes"}'
```

`X-Actor: hermes` sorgt dafür, dass jede Schreibaktion unter diesem Namen im Verlauf steht.

## Fehlerbilder

| Symptom | Ursache |
|---|---|
| `401 Authentication required` | Key fehlt oder falsch; Header muss `Authorization: Bearer …` sein |
| `406 Not Acceptable` | Client sendet nicht `Accept: application/json, text/event-stream` — MCP-Client nutzen, nicht curl |
| Verbindung steht, aber 0 Werkzeuge | falsche URL — `/mcp/` mit Schrägstrich am Ende |
| Werkzeuge da, Antworten inhaltlich falsch | `SKILL.md` nicht geladen (Feldnamen/Tags unbekannt) |
