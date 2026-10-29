# Auftrag an Codex — Ilvana-MCP verdrahten

**Auftrag:** Codex soll Kandidatenfragen ausschließlich über das Ilvana-MCP beantworten.
Halte dich exakt an die Schritte. Es gibt keine Alternativen außer den ausdrücklich genannten
Wenn-dann-Fällen. Erfinde keine Pfade — ermittle sie wie angegeben und nenne sie im Bericht.

## Zielstruktur (was am Ende existieren muss)

| Artefakt | Pfad / Ort |
|---|---|
| Regeldatei | `AGENTS.md` im Repo-Wurzelverzeichnis (Codex liest sie automatisch) |
| Skill | `skills/ilvana-airtable/SKILL.md` + `references/` (im Repo vorhanden, nur lesen) |
| Transport | MCP falls die Version es unterstützt, sonst REST über `scripts/ilvana.sh` |

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

1. **Repo bereitstellen:** `git clone https://github.com/dsactivi-2/Airtable-mcp.git && cd Airtable-mcp`
2. **Umgebung:** `export CODEWORDS_API_KEY="<DEIN_KEY>" ILVANA_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7" ILVANA_ACTOR="codex"`
3. **Transport wählen — genau eine Regel:**
   - MCP vorhanden (`codex --help` oder Doku) → Eintrag wie bei Hermes, `X-Actor: codex`.
   - Kein MCP → REST über `./scripts/ilvana.sh <werkzeug> '<json>'`.
   Andere Wege sind nicht vorgesehen.
4. **Regelblock einfügen** in `./AGENTS.md` nach der Einfügeregel.
5. **Selbsttest:** `python3 scripts/test_mcp_e2e.py "Mihaljevic"` und
   `./scripts/ilvana.sh audit_list '{"limit":5,"actor":"codex"}'`.

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
Framework          : Codex
Transport          : <gewählter Weg>
Pfad Regeldatei    : <absoluter Pfad>   (ChatGPT/Grok: "Instructions-Feld")
BEGIN-Marker       : <Anzahl>
Werkzeuge          : <Anzahl>
Selbsttest         : <grün/rot je Prüfung>
Repo-Wurzel        : <Pfad>
Offene Punkte      : <keine | was genau>
```