# Einrichtung und Nutzung

Der Dienst ist **online** und bereits deployed. Nichts läuft lokal. Diese Anleitung führt von null
bis zum laufenden Betrieb.

- REST: `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7`
- MCP:  `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/`

---

## 1. Die drei Variablen im Integrations-Panel

Im Panel siehst du `HOOK_SECRET`, `AIRTABLE_PAT` und `ALERT_WEBHOOK_URL`. Das sind die einzigen
Zugangsdaten des Dienstes.

| Variable | Pflicht | Woher | Wozu |
|---|---|---|---|
| `AIRTABLE_PAT` | **ja** | Airtable selbst (siehe Abschnitt 2) | Lesen und Schreiben beider Bases, Datei-Uploads |
| `HOOK_SECRET` | nein | **erfindest du selbst** — kein Anbieter | schützt `POST /hooks/airtable` davor, von Fremden aufgerufen zu werden |
| `ALERT_WEBHOOK_URL` | nein | **deine eigene Plattform** | dorthin schickt der Dienst Fehler- und Auffälligkeits-Alarme |

### HOOK_SECRET — woher?

Es gibt keinen Anbieter und keinen Aussteller. Du legst den Wert selbst fest, zum Beispiel:

```bash
openssl rand -hex 32
# 9f2c…  →  diesen Wert hier eintragen UND in der Airtable-Automation als Header
```

Er muss nirgends „beantragt“ werden. Er ist nur ein gemeinsames Passwort zwischen Airtable und dem
Dienst: der Dienst akzeptiert den Hook-Aufruf nur, wenn der Header `X-Hook-Secret` exakt diesen Wert
enthält.

Wichtig: Ist `HOOK_SECRET` **leer**, ist `/hooks/airtable` offen — dann kann jeder mit der Dienst-URL
Automatikläufe auslösen. Deshalb beim Anbinden der Airtable-Automation immer setzen.

### ALERT_WEBHOOK_URL — woher?

Das ist eine Adresse **deiner** Plattform, die JSON per POST annimmt und auf Mail, Viber, Facebook
Messenger oder SMS verteilt. Konkret brauchst du dort einen eingehenden Webhook (je nach Plattform
„Incoming Webhook“, „HTTP-Empfänger“ oder ein eigener Endpunkt).

Solange die Variable leer ist, geht **nichts verloren**: Alarme werden gespeichert und sind über das
Werkzeug `alerts_list` abrufbar (mit dem Hinweis `webhook_configured: false`). Erst mit gesetzter URL
kommt zusätzlich die Push-Meldung.

Der Dienst schickt dieses JSON:

```json
{
  "service": "ilvana-airtable",
  "at": "2026-10-29 05:26",
  "kind": "tool_error",
  "message": "application_update: Nicht schreibbare Felder …",
  "details": {"tool": "application_update", "status": 400},
  "actor": "z0xsf0pldjxndz50ef5zwmx8"
}
```

`kind` ist einer von: `tool_error`, `tool_crash`, `validation_error`, `data_health`.

### Werte eintragen

Im Panel auf **Add** klicken, Wert einfügen, speichern. Der Dienst liest die Variablen bei jedem Aufruf
neu — ein erneutes Deployment ist normalerweise nicht nötig. Wenn ein Wert nicht ankommt: einmal neu
deployen.

---

## 2. Airtable-Token (`AIRTABLE_PAT`)

1. airtable.com öffnen → oben rechts auf das Konto → **Developer hub**
2. **Personal access tokens** → **Create new token**
3. Scopes anhaken:
   - `data.records:read`
   - `data.records:write`
   - `schema.bases:read`
4. Unter **Access** beide Bases hinzufügen:
   - *Ilvana i Hase (Kopieren)* ← Standard
   - *Ilvana i Hase* ← nur nötig, wenn auch die Original-Base beschrieben werden soll
5. Token kopieren (beginnt mit `pat…`) und als `AIRTABLE_PAT` eintragen

Fehlt eine Base im Token, antwortet der Dienst mit `Kein Zugriff auf diese Airtable-Base` — nicht mit
falschen Daten. Nachträglich lässt sich der Zugriff jederzeit im Token erweitern.

---

## 3. Agenten verbinden

Der einzige Schlüssel, den ein Agent bekommt, ist der **CodeWords API Key**
(codewords.agemo.ai → Einstellungen → API-Keys). Der Airtable-Token bleibt im Dienst.

### Hermes Agent (MCP)

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

Zusätzlich `skills/ilvana-airtable/SKILL.md` als Wissen laden.

### Codex

Entweder derselbe MCP-Block, oder REST plus Repo-Wissen (`AGENTS.md` liest Codex automatisch):

```bash
export ILVANA_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
export CODEWORDS_API_KEY="<key>"
curl -s -X POST "$ILVANA_URL/tools/candidates_search" \
  -H "Authorization: Bearer $CODEWORDS_API_KEY" -H "Content-Type: application/json" \
  -d '{"query":"Mihaljevic","limit":5}'
```

### ChatGPT (eigener GPT)

1. GPT → *Configure* → *Actions* → *Create new action*
2. Schema importieren: Inhalt von `openapi/ilvana-airtable.openapi.json`
3. Authentication: **API Key**, Auth Type **Bearer**, Key = CodeWords API Key
4. Instructions: Inhalt von `skills/ilvana-airtable/SKILL.md`

### Grok (Web)

Kein MCP-Connector. Custom Action mit derselben OpenAPI-Datei importieren (Bearer-Auth), sonst die
Werkzeugdefinitionen aus `…/schema/tools` in den Funktionskatalog laden. Schlüssel gehört in die
Konfiguration, nie in den Prompt.

---

## 4. Erste Aufrufe

```jsonc
// Wer ist das?
{"query": "Mihaljevic"}                       → candidates_search

// Komplette Akte für einen Anruf
{"record_id": "recuQxflPVccPo9xT"}            → candidate_dossier

// Was ist überfällig?
{"only_overdue": true}                        → applications_search

// Überblick
{}                                            → pipeline_summary

// Notiz anhängen
{"record_id": "rec…", "note": "Rückruf 14:00"} → application_add_note

// Datei hochladen (PDF, JPG, PNG, DOC, DOCX, max. 10 MB)
{"record_id": "rec…", "field": "Lebenslauf", "file": "https://…/cv.pdf"} → document_upload
```

Jeder Aufruf ist `POST /tools/<name>` mit JSON-Body. Antworten haben immer `success` und `result`.

---

## 5. Airtable-Automation anbinden

Damit der Dienst in Sekunden reagiert statt am nächsten Morgen:

1. In Airtable eine **Automation** anlegen
2. Trigger: *When record matches conditions* (z. B. `Status kandidata` ist `Casting`) oder
   *When record updated*
3. Aktion: **Run script** oder **Webhook** → `POST`
   `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/hooks/airtable`
4. Header:
   - `Content-Type: application/json`
   - `X-Hook-Secret: <dein HOOK_SECRET>`
   - `Authorization: Bearer <CODEWORDS_API_KEY>`
5. Body:

```json
{
  "record_id": "<Record-ID aus der Automation>",
  "mode": "preview",
  "event": "Status gewechselt"
}
```

**Erst mit `preview` testen** — der Dienst antwortet mit dem geplanten Vorgang, schreibt aber nichts.
Wenn das Ergebnis passt, in der Automation auf `"mode": "apply"` stellen.

Antwort:

```json
{"success": true, "event": "Status gewechselt",
 "automation": {"mode": "preview", "planned": 1, "actions": [...]}}
```

---

## 6. Tageslauf

Registriert als Vorschau, täglich 07:00 Europe/Sarajevo, verwaltbar unter
[codewords.agemo.ai/scheduled](https://codewords.agemo.ai/scheduled).

- Vorschau: `POST /automation/daily?mode=preview`
- Echt: `POST /automation/daily?mode=apply`

Inhalt: überfällige Aktionen, Termine der nächsten 7 Tage, fehlende Unterlagen, geplante Folgeaufgaben
und der Ergebnis der Qualitätsprüfung (`health`).

---

## 7. Alarme prüfen

```jsonc
{}                      → alerts_list      // gespeicherte Alarme
{"limit": 20}           → error_log        // fehlgeschlagene Aufrufe
{}                      → data_health      // Lücken und Dubletten
```

Test eines Alarms ohne echten Schaden: ein bewusst nicht schreibbares Feld senden, z. B.
`{"record_id": "rec…", "fields": {"Obrazovanje (norm.)": "Da"}}` an `application_update`.
Der Aufruf scheitert kontrolliert und erscheint in `error_log` und `alerts_list`.

---

## 8. Verlauf lesen — wer hat was gemacht?

```jsonc
{"limit": 20}                                 → letzte Schreibaktionen
{"record_id": "recPceen76ZUQ29MI"}            → alles zu einem Datensatz
{"actor": "hermes"}                           → alles von einem Agenten
```

Damit Agenten unterscheidbar sind, beim Aufruf mitsenden:

```
X-Actor: hermes
```

Ohne diesen Header protokolliert der Dienst die Aufrufer-ID der Plattform.

---

## 9. Grenzen und Hygiene

- `base=kopieren` ist Standard; `original` nur auf ausdrückliche Anweisung
- Schreibzugriff nur auf freigegebene Felder, Auswahlwerte werden validiert
- Kein Löschen, keine Massenbereinigung ohne `dry_run` + `confirm`
- CodeWords Key wie ein Passwort behandeln; bei Verlust erneuern (Airtable bleibt unberührt)
- Keine Schlüssel in Chat-Prompts — nur in Konfiguration oder Umgebung

---

## 10. Fehlersuche

| Symptom | Ursache / Lösung |
|---|---|
| `401 Authentication required` | Key fehlt oder falscher Header (`Authorization: Bearer …`) |
| `406 Not Acceptable` bei `/mcp/` | roher curl statt MCP-Client — der Client muss `Accept: application/json, text/event-stream` senden |
| `Kein Zugriff auf diese Airtable-Base` | Base fehlt im Airtable-Token unter Access |
| `Ungültiges Hook-Secret` | `X-Hook-Secret` fehlt oder weicht von `HOOK_SECRET` ab |
| `Nicht schreibbare Felder …` | Formel/Verknüpfung/Anhang angesprochen — erlaubte Felder stehen in der Meldung |
| Alarme kommen nicht an | `ALERT_WEBHOOK_URL` leer → nur gespeichert; `alerts_list` zeigt `webhook_configured` |

---

## 11. Hook testen, Konfiguration ändern, Base erweitern

Alles drei geht **über den Agenten** — kein Panel, kein Redeploy.

### Hook testen (schreibt nichts)

```json
POST /tools/hook_test {"record_id": "rec…"}
```

Antwort: Hook-URL, benötigte Header, Beispiel-Body, fertiger `curl`, Warnung falls kein Secret gesetzt
ist, und `would_do` — was ein echter Aufruf auslösen würde. Erst danach die Airtable-Automation scharf
schalten.

### Konfiguration über den Agenten

```json
POST /tools/config_get {}
POST /tools/config_set {"alert_webhook_url": "https://<deine-plattform>/incoming/abc"}
POST /tools/config_set {"hook_secret": "<16+ Zeichen, z.B. openssl rand -hex 32>"}
POST /tools/config_set {"default_base": "original"}
POST /tools/config_set {"clear": ["alert_webhook_url"]}
```

Werte greifen sofort. Secrets werden nur als `gesetzt: true/false` zurückgegeben.
`AIRTABLE_PAT` bleibt bewusst außen vor — nur im Platform-Panel änderbar.

### Base-Struktur erweitern

```json
POST /tools/field_create {"table": "prijave", "name": "Rückruf notiert",
  "type": "singleSelect", "options": {"choices": [{"name": "ja"}, {"name": "nein"}]}}

POST /tools/table_create {"name": "Prüfliste",
  "fields": [{"name": "Name", "type": "singleLineText"}, {"name": "Datum", "type": "date"}]}

POST /tools/field_update {"table": "prijave", "field_id": "fld…",
  "options": {"choices": [{"name": "Offen"}, {"name": "Erledigt"}]}}
```

Standard ist **Vorschau** (`preview=true`): der Dienst zeigt Methode, URL und Payload, sendet aber nichts.
Echt wird es nur mit `preview=false` **und** `confirm=true`.

Voraussetzung: der Airtable-Schlüssel braucht zusätzlich **`schema.bases:write`**. Kein Löschen von
Tabellen oder Feldern, kein Umbau von Feldtypen.
