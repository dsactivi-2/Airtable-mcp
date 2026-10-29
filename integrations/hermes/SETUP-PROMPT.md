# Auftrag an Hermes — Ilvana-Airtable-MCP verdrahten

Kopiere den Text ab „AUFTRAG" in deine Hermes-Sitzung (nach dem Verbinden mit dem Mac).

---

## AUFTRAG

Du bist Hermes auf diesem Mac. Der Dienst **Ilvana Airtable MCP** läuft und ist erreichbar.
Verdrahte ihn dauerhaft als primäre Datenquelle für alle Kandidatenfragen.

**Wichtig — beobachteter Fehler, den du behebst:** Auf die Frage „Wer ist Haris Mihaljevic?" hast du
Google, DuckDuckGo, Bing, judo.hr und Wikipedia abgefragt. Das war falsch: Der Kandidat steht in der
Airtable-Datenbank, nicht im Web — und ein Kandidatenname gehört nicht in eine Suchmaschine.
Ab jetzt gilt: Kandidatenfragen gehen **ausschließlich** an das MCP.

### Schritt 1 — Erreichbarkeit prüfen

```bash
export CODEWORDS_API_KEY="<DEIN_KEY>"
curl -s -H "Authorization: Bearer $CODEWORDS_API_KEY" \
  https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/health
```

Erwartet: `{"status":"ok","version":"1.5.6","tools":31,...}`.
Kommt kein `ok`, brich ab und melde den Fehler — nicht weiterarbeiten.

### Schritt 2 — MCP-Server eintragen

Trage in deiner MCP-Konfiguration ein:

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": {
        "Authorization": "Bearer <DEIN_KEY>",
        "X-Actor": "hermes"
      }
    }
  }
}
```

### Schritt 3 — AGENTS.md ergänzen

Hänge folgenden Block an deine `AGENTS.md` an (bestehenden Inhalt nicht überschreiben):

```markdown
## Ilvana Airtable MCP — verbindliche Regeln

Der MCP ist die einzige Quelle für Kandidaten-, Bewerbungs- und Prozessdaten.
31 Werkzeuge, Endpunkt: https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/

1. **Routing:** Jede Frage zu Kandidaten, Bewerbungen, Status, Terminen, Dokumenten, Casting,
   Vertrag oder Visum geht an dieses MCP. **Niemals** Google/Bing/DuckDuckGo oder Web-Fetch
   für Personennamen — falsche Quelle und Datenschutzverstoß.
2. **Erst lesen, dann schreiben:** `candidates_search` → `candidate_dossier` → erst dann ändern.
3. **Aufrufer-Kennung:** jeder Aufruf mit `X-Actor: hermes`, damit Aktionen im Verlauf zuzuordnen sind.
4. **Nur freigegebene Felder:** Formeln (`Obrazovanje (norm.)`, `Njemački`, `Vozačka`,
   `Test oznaka`, `Lični podaci – nedostaje`) und Anhang-Felder sind nicht schreibbar.
5. **Massenänderung:** immer erst `dry_run: true` zeigen, echte Ausführung nur mit
   `dry_run: false` **und** `confirm: true`, maximal 50 Datensätze.
6. **Keine Löschungen** — weder Datensätze, Dateien, Tabellen noch Felder.
7. **Bei Fehlern nicht raten:** `service_info` (Version, Secrets), `error_log` (Ursache),
   `data_health` (Datenqualität) aufrufen.
8. **Antwortstil:** Deutsch, Namen statt Record-IDs, am Ende immer: welche Felder geändert wurden.
9. **Kein Secret in den Chat:** der Key gehört in die Konfiguration, nicht in eine Nachricht.
```

### Schritt 4 — Skill-Datei schreiben

Lege `references/airtable-mcp.md` in deinem Skill `hermes-mcp-http` an (oder aktualisiere sie):

```markdown
# Ilvana Airtable MCP — Werkzeugreferenz

## Verbindung
MCP: https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/
Auth: Authorization: Bearer <CODEWORDS_API_KEY> · Header X-Actor: hermes
REST-Alternative: POST .../tools/<name> mit JSON-Body
Funktionsdefinitionen: GET .../schema/tools · OpenAPI: .../openapi.json

## Werkzeuggruppen (31)
- Lesen: schema_get, candidates_search, applications_search, candidate_dossier,
  application_get, documents_list, casting_ratings_list, pipeline_summary, due_report
- Schreiben: application_create, application_update, applications_bulk_update,
  application_add_note, casting_rating_upsert, document_upload, tasks_manage
- Automatik: automation_rules, automation_run, automation_log
- Betrieb: audit_list, error_log, alerts_list, data_health, hook_test,
  config_get, config_set, service_info, schedule_sync
- Struktur: table_create, field_create, field_update

## Typische Aufrufe
```json
{"query": "Mihaljevic"}                          → candidates_search
{"phone": "+387 61 614 368"}                     → candidates_search (Handy oder Festnetz)
{"record_id": "recuQxflPVccPo9xT"}               → candidate_dossier
{"status_kandidata": "Casting", "only_overdue": true} → applications_search
{"record_id": "rec…", "note": "Rückruf 14:00"}   → application_add_note
{"fields": {"Ime i prezime": "…", "Broj telefona": "…"}} → application_create
```

## Feldnamen (häufig)
Ime i prezime · Ime · Prezime · Pozivni broj · Broj telefona · Status kandidata ·
Casting grupa · Casting ishod · Ugovor tok · Viza ishod · Termin casting · Termin vize ·
Datum početka rada · Dokumenti · Bilješka · Sljedeća akcija · Rok akcije · Kundennummer · Br. pasoša

Statuswerte (exakt): Zainteresiran, Zeleni / obrada, Pre-casting, Casting, Primljeni, Ugovor,
Predsaglasnost, Slanje potpisanih ugovora, Viziranje, Čekanje vize, Čeka početak rada,
„Počeo sa radom " (mit Leerzeichen), ODBIJEN, Odustao

## Fehlerbilder
401 → Key fehlt/falsch · 403 → Base nicht im Airtable-Token · 
„Nicht schreibbare Felder …" → Formel/Anhang, erlaubte Felder stehen in der Meldung ·
409 → doppelte Telefonnummer bei application_create
```

### Schritt 5 — Selbsttest (Pflicht, nicht überspringen)

Führe diese vier Aufrufe aus und zeige die Ergebnisse:

1. `candidates_search` mit `{"query": "Mihaljevic"}` → erwartet **1 Treffer**, Record `recuQxflPVccPo9xT`
2. `candidate_dossier` mit dieser Record-ID → erwartet Status, Telefon, `pre_call_brief`
3. `service_info` ohne Argumente → erwartet Version `1.5.6`, `tools: 31`, alle drei Secrets `true`
4. `audit_list` mit `{"limit": 5, "actor": "hermes"}` → erwartet die eben ausgeführten Aktionen

**Melde erst „verdrahtet", wenn alle vier grün sind.** Bei einem Fehlschlag: Ursache aus `error_log`
nennen, nicht ausweichen.

### Schritt 6 — Verhalten ab jetzt

- Frage „Wer ist Haris Mihaljevic?" → `candidates_search`, nicht Websuche.
- Frage „Was ist überfällig?" → `applications_search` mit `only_overdue`.
- Frage „Wie ist der Stand?" → `pipeline_summary`, optional `data_health`.
- Änderungen nur nach `candidate_dossier` und mit klarer Ansage, was geändert wird.

### Was du nicht tust

- Keine Websuche nach Kandidatennamen (Datenschutz, falsche Quelle).
- Keine Secrets in Dateien, die im Repo landen, oder in Chat-Antworten.
- Keine Massenänderung ohne `confirm`.
- Keine Löschvorgänge.
