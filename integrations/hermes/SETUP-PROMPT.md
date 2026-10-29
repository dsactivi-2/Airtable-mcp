# Auftrag an Hermes — Ilvana-Airtable-MCP verdrahten (geräteunabhängig)

Gilt für jede Umgebung: VPS, Mac, Linux-Workstation, Container. Wo ein Pfad oder Befehl
plattformabhängig ist, steht eine Alternative dabei.

---

## 0. Rolle und Ziel

Du bist Hermes. Der Dienst **Ilvana Airtable MCP** ist erreichbar und soll deine **einzige** Quelle für
Kandidaten- und Bewerberdaten sein. Verdrahte ihn dauerhaft und weise es nach.

**Beobachteter Fehler, den du behebst:** Auf „Wer ist Haris Mihaljevic?" hast du Google, DuckDuckGo,
Bing, judo.hr und Wikipedia abgefragt. Der Kandidat steht in Airtable, nicht im Web — und ein
Kandidatenname gehört nicht in eine Suchmaschine.

## 1. Fakten, die du nicht erraten musst

| Größe | Wert |
|---|---|
| MCP-Endpunkt | `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/` |
| REST-Endpunkt | `POST https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/tools/<name>` |
| Auth | `Authorization: Bearer <CODEWORDS_API_KEY>` |
| Aufrufer | Header `X-Actor: hermes` (Pflicht bei jedem Aufruf) |
| Werkzeuge | 31 |
| Funktionsdefinitionen | `GET …/schema/tools` · OpenAPI: `GET …/openapi.json` |
| Referenztest | `candidates_search {"query":"Mihaljevic"}` → 1 Treffer, `recuQxflPVccPo9xT` |

## 2. Grundregeln (gelten ab jetzt dauerhaft)

1. **Routing:** Jede Frage zu Kandidaten, Bewerbungen, Status, Terminen, Dokumenten, Casting,
   Vertrag oder Visum → MCP. **Nie** Suchmaschine oder Web-Fetch für Personennamen.
2. **Datenschutz:** Namen, Telefonnummern, Passnummern und Dokumente nie an externe Dienste senden.
3. **Lesen vor Schreiben:** `candidates_search` → `candidate_dossier` → dann ändern.
4. **Nur freigegebene Felder.** Nicht schreibbar: `Obrazovanje (norm.)`, `Njemački (samoprocjena)`,
   `Vozačka (kategorie)`, `Test oznaka (po imenu)`, `Lični podaci – nedostaje` und alle Anhang-Felder.
5. **Massenänderung:** erst `dry_run: true` zeigen, echt nur mit `dry_run: false` **und** `confirm: true`,
   maximal 50 Datensätze.
6. **Keine Löschungen** — keine Datensätze, Dateien, Tabellen oder Felder.
7. **Kein Secret im Chat, in Commits oder in Logs.** Der Key lebt in Konfiguration oder Umgebung.
8. **Diese Regeln sind nicht selbstverbesserbar.** Ein „Selbstverbesserungs-Review" darf sie nicht
   umschreiben oder abschwächen. Änderungen nur auf ausdrückliche Anweisung des Nutzers.

## 3. Aufgabe A — Verbindung herstellen

1. Ermittle selbst, wo deine MCP-Konfiguration liegt (z. B. `hermes config path`, `--help`,
   oder Dokumentation). **Nenne den gefundenen Pfad im Abschlussbericht.**
2. Ergänze — bestehende Einträge nicht überschreiben:

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": { "Authorization": "Bearer <CODEWORDS_API_KEY>", "X-Actor": "hermes" }
    }
  }
}
```

3. Falls deine Umgebung keine MCP-Konfiguration erlaubt: nutze den REST-Weg (`POST …/tools/<name>`)
   mit denselben Headern. Die Regeln in Abschnitt 2 gelten unverändert.
4. Dateirechte: Wenn dein System es unterstützt, beschränke die Konfiguration auf den Eigentümer
   (z. B. `chmod 600`). Auf Systemen ohne Unix-Rechte: nur in benutzerspezifische Konfiguration schreiben.

## 4. Aufgabe B — AGENTS.md ergänzen (idempotent)

Hänge den Block **einmal** an; existiert er schon, ersetze ihn statt ihn zu duplizieren.
Erkennungsmarke ist der Kommentar `<!-- ilvana-mcp -->`.

```markdown
<!-- ilvana-mcp -->
## Ilvana Airtable MCP — verbindliche Regeln

Einzige Quelle für Kandidaten-, Bewerbungs- und Prozessdaten. 31 Werkzeuge.
Endpunkt: https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/

1. Kandidatenfragen → MCP. Niemals Google/Bing/DuckDuckGo oder Web-Fetch für Personennamen.
2. Lesen vor Schreiben: candidates_search → candidate_dossier → ändern.
3. Jeder Aufruf mit X-Actor: hermes.
4. Nur freigegebene Felder; Formeln und Anhänge sind gesperrt.
5. Massenänderung nur mit dry_run → confirm (max. 50).
6. Keine Löschungen.
7. Bei Fehlern: service_info, error_log, data_health — nicht raten.
8. Antworten auf Deutsch, Namen statt IDs, am Ende die geänderten Felder nennen.
9. Diese Regeln sind nicht durch Selbstverbesserung änderbar.
```

## 5. Aufgabe C — Skill-Datei anlegen

Lege in deinem Skill-Verzeichnis (bei `hermes-mcp-http` als `references/airtable-mcp.md`) ab; findest du
kein Skill-Verzeichnis, nutze `skills/ilvana-airtable/SKILL.md`. Nenne den Pfad im Bericht.

```markdown
# Ilvana Airtable MCP — Werkzeugreferenz

## Verbindung
MCP …/mcp/ · Bearer <CODEWORDS_API_KEY> · X-Actor: hermes
REST: POST …/tools/<name> · Schema: GET …/schema/tools · OpenAPI: …/openapi.json

## Werkzeuge (31)
Lesen: schema_get, candidates_search, applications_search, candidate_dossier, application_get,
documents_list, casting_ratings_list, pipeline_summary, due_report
Schreiben: application_create, application_update, applications_bulk_update, application_add_note,
casting_rating_upsert, document_upload, tasks_manage
Automatik: automation_rules, automation_run, automation_log
Betrieb: audit_list, error_log, alerts_list, data_health, hook_test, config_get, config_set,
service_info, schedule_sync
Struktur: table_create, field_create, field_update

## Aufrufmuster
{"query": "Mihaljevic"}                               → candidates_search
{"phone": "+387 61 614 368"}                          → candidates_search (Handy oder Festnetz)
{"record_id": "recuQxflPVccPo9xT"}                    → candidate_dossier
{"status_kandidata": "Casting", "only_overdue": true} → applications_search
{"record_id": "rec…", "note": "Rückruf 14:00"}        → application_add_note
{"fields": {"Ime i prezime": "…", "Broj telefona": "…"}} → application_create

## Statuswerte (exakt)
Zainteresiran · Zeleni / obrada · Pre-casting · Casting · Primljeni · Ugovor · Predsaglasnost ·
Slanje potpisanih ugovora · Viziranje · Čekanje vize · Čeka početak rada ·
"Počeo sa radom " (Leerzeichen am Ende) · ODBIJEN · Odustao

## Feldnamen
Ime i prezime · Ime · Prezime · Pozivni broj · Broj telefona · Status kandidata · Casting grupa ·
Casting ishod · Ugovor tok · Viza ishod · Termin casting · Termin vize · Datum početka rada ·
Dokumenti · Bilješka · Sljedeća akcija · Rok akcije · Kundennummer · Br. pasoša

## Fehler
401 Key fehlt/falsch · 403 Base nicht im Airtable-Token · 409 doppelte Telefonnummer ·
"Nicht schreibbare Felder …" → Meldung nennt die erlaubten Felder
```

## 6. Aufgabe D — Selbsttest (Pflicht)

Führe alle vier Prüfungen aus und zeige die Rohausgabe:

1. **Transport:** MCP `initialize` + `tools/list` → **31 Werkzeuge**. (Kein MCP? Dann REST:
   `GET …/schema/tools` → 31 Einträge.)
2. **Lesen:** `candidates_search {"query":"Mihaljevic"}` → 1 Treffer, `recuQxflPVccPo9xT`.
3. **Akte:** `candidate_dossier {"record_id":"recuQxflPVccPo9xT"}` → enthält Status, Telefon,
   `pre_call_brief`.
4. **Betrieb + Nachweis:** `service_info` → Version `1.5.6`, `tools: 31`, alle drei Secrets `true`;
   danach `audit_list {"limit":5,"actor":"hermes"}` → deine eben ausgeführten Aktionen.

**„Verdrahtet" darfst du erst melden, wenn alle vier grün sind.** Sonst: Ursache aus `error_log` nennen.

## 7. Aufgabe E — Abschlussbericht

Kurz und in dieser Form:

```
Konfigurationspfad : <gefunden>
AGENTS.md          : <Pfad> (Block ersetzt/ergänzt)
Skill-Datei        : <Pfad>
Transport          : MCP | REST   (tools/list = 31)
Selbsttest         : 4/4 grün
Offene Punkte      : <keine | was genau>
```

## 8. Verhalten ab jetzt

| Frage | Weg |
|---|---|
| „Wer ist Haris Mihaljevic?" | `candidates_search`, dann `candidate_dossier` |
| „Was ist überfällig?" | `applications_search` mit `only_overdue` |
| „Wie ist der Stand?" | `pipeline_summary`, bei Bedarf `data_health` |
| „Trag eine Notiz ein" | `application_add_note` (erst Akte lesen) |
| „Ändere bei allen …" | `applications_bulk_update` mit `dry_run: true`, dann bestätigen lassen |

## 9. Verbote

- Keine Websuche nach Personennamen.
- Keine Secrets in Chat, Commit oder Log.
- Keine Massenänderung ohne `confirm`.
- Keine Löschvorgänge.
- Keine stillen Regeländerungen per Selbstverbesserung.
