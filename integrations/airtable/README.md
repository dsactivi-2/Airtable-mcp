# Airtable-Automation anbinden

Ziel: eine Statusänderung in Airtable löst **sofort** die Automatik aus, statt auf den Tageslauf zu warten.

## Vorbereiten

1. Base **Ilvana i Hase (Kopieren)** → Tab *Automations* → *Create automation*
2. Trigger: *When record matches conditions* (z. B. `Status kandidata` ist `Casting`)
   oder *When record updated* auf *Prijave (test)*
3. Aktion hinzufügen: **Run a script**
4. Links unter *Input variables* → *Add input variable*
   - Name: `recordId`
   - Value: *Record ID* (Dynamic token des Triggers)

## Skript einsetzen

Inhalt von `automation-script.js` einfügen und ersetzen:

- `REPLACE_WITH_CODEWORDS_API_KEY` → dein CodeWords-Key
- `REPLACE_WITH_HOOK_SECRET` → dein Hook-Secret

`MODE = "preview"` **stehen lassen**, solange du testest.

## Testen

Automation manuell starten, Skript-Log ansehen:

```json
{"success":true,"event":"Airtable-Automation",
 "automation":{"mode":"preview","planned":1,"actions":[{"name":"…","rule":"status_casting"}]}}
```

- `200` + `planned: 0` → Verbindung steht, für diesen Datensatz greift keine Regel
- `401` → `hook_secret` fehlt oder weicht ab
- `403` → CodeWords-Key falsch

## Scharf stellen

`MODE = "apply"` setzen, Automation aktivieren. Jeder Datensatz wird pro Regel genau einmal
verändert; jede Änderung steht danach in `audit_list`.

## Warum nicht die Aktion „Webhook"?

Sie kann keine eigenen Header setzen — ohne `Authorization: Bearer …` antwortet die Plattform mit 401.
Und das Hook-Secret muss ohnehin in den Body, weil das Gateway den Header `X-Hook-Secret` entfernt.
