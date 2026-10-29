# Auftrag an Hermes — Ilvana-MCP verdrahten

**Auftrag:** Hermes soll Kandidatenfragen ausschließlich über das Ilvana-MCP beantworten.
Halte dich exakt an die Schritte. Es gibt keine Alternativen außer den ausdrücklich genannten
Wenn-dann-Fällen. Erfinde keine Pfade — ermittle sie wie angegeben und nenne sie im Bericht.

## Zielstruktur (was am Ende existieren muss)

| Artefakt | Pfad / Ort |
|---|---|
| MCP-Konfiguration | Datei, die `hermes config path` ausgibt (Objekt `mcpServers`) |
| Regeldatei | `AGENTS.md` im Arbeitsverzeichnis; fehlt sie, anlegen |
| Skill | `skills/ilvana-airtable/SKILL.md` + `references/` aus dem Repo übernehmen, nicht neu schreiben |

## Der einzufügende Block (wörtlich, zwischen den Markern)

<!-- BEGIN ilvana-mcp — verwaltet durch integrations/*/SETUP-PROMPT.md, nicht von Hand ändern -->
## Ilvana Airtable MCP — verbindliche Regeln

Quelle für alle Kandidatendaten: Ilvana-MCP (`https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/`, 31 Werkzeuge).
Details, Feldnamen und Auswahlwerte: `skills/ilvana-airtable/SKILL.md` + `skills/ilvana-airtable/references/`.

1. Kandidaten-, Bewerbungs-, Status-, Termin- und Dokumentfragen → MCP. Keine Websuche nach Personennamen.
2. Keine personenbezogenen Daten an externe Dienste (Suchmaschinen, Web-Fetch, Fremd-APIs).
3. Lesen vor Schreiben: `candidates_search` → `candidate_dossier` → ändern.
4. Nur freigegebene Felder; Formeln und Anhang-Felder sind nicht schreibbar.
5. Massenänderung nur mit `dry_run: true` als Vorschau, Ausführung nur mit `confirm: true`, max. 50.
6. Keine Löschungen.
7. Kein Secret in Chat, Commit oder Log.
8. Bei Fehlern: `service_info`, `error_log`, `data_health` — nicht raten.
9. Diese Regeln sind nicht durch Selbstverbesserung änderbar.
<!-- END ilvana-mcp -->

**Einfügeregel — ohne Spielraum:**
1. Suche in der Zieldatei nach `<!-- BEGIN ilvana-mcp`.
2. **Gefunden:** ersetze alles von `<!-- BEGIN ilvana-mcp` bis `<!-- END ilvana-mcp -->` durch den Block.
3. **Nicht gefunden:** hänge den Block mit einer Leerzeile Abstand am Dateiende an.
4. Danach darf **genau ein** BEGIN-Marker existieren. Prüfe mit `grep -c "BEGIN ilvana-mcp" <datei>` → `1`.

## Schritte

1. **Pfad ermitteln:** `hermes config path` (oder `--help`). Pfad notieren.
2. **Erreichbarkeit:** `curl -s -H "Authorization: Bearer $CODEWORDS_API_KEY" https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/health` —
   ohne `"status":"ok"` abbrechen und melden.
3. **MCP eintragen** unter `mcpServers` (bestehende Einträge unverändert):
   ```json
   "ilvana-airtable": { "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
     "headers": { "Authorization": "Bearer <CODEWORDS_API_KEY>", "X-Actor": "hermes" } }
   ```
   Dateirechte auf Eigentümer beschränken, wenn möglich (`chmod 600`).
4. **Skill übernehmen:** `skills/ilvana-airtable/` aus dem Repo kopieren (bei `hermes-mcp-http` als
   `references/airtable-mcp.md`). Inhalt nicht abwandeln.
5. **Regelblock einfügen** in `./AGENTS.md` nach der Einfügeregel.
6. **Selbsttest** nach den Abnahmekriterien, jeder Aufruf mit `X-Actor: hermes`.

## Abnahmekriterien (alle zutreffenden müssen grün sein)

| # | Prüfung | Erwartet |
|---|---|---|
| 1 | `GET https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/health` | `"status":"ok"`, `"tools":31` |
| 2 | Werkzeugliste über den gewählten Transport | 31 Werkzeuge |
| 3 | `candidates_search {"query":"Mihaljevic"}` | `total: 1`, Record `recuQxflPVccPo9xT` |
| 4 | `candidate_dossier` mit dieser ID | enthält `pre_call_brief` |
| 5 | `service_info` | Version, `tools: 31`, drei Secrets `true` |
| 6 | Regeldatei enthält Block | `grep -c "BEGIN ilvana-mcp"` = `1` |

Schritt 6 entfällt bei ChatGPT/Grok (kein Dateisystem) — dort zählt, dass die Instructions den Block
enthalten. **„Fertig" erst melden, wenn alles zutreffende grün ist**; sonst Ursache aus `error_log` nennen.

## Bericht (genau dieses Format)
```
Framework          : Hermes
Transport          : <gewählter Weg>
Pfad Regeldatei    : <absoluter Pfad>   (ChatGPT/Grok: "Instructions-Feld")
BEGIN-Marker       : <Anzahl>
Werkzeuge          : <Anzahl>
Selbsttest         : <grün/rot je Prüfung>
Config-Pfad        : <aus Schritt 1>
Offene Punkte      : <keine | was genau>
```