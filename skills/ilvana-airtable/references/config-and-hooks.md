# Konfiguration, Hook-Test und Base-Änderungen

## Konfiguration lesen

```json
POST /tools/config_get {}
```

```json
{"default_base": "kopieren", "alert_webhook_url": null, "alert_webhook_configured": false,
 "hook_secret_configured": false, "overrides_in_use": []}
```

Secrets werden **nie** im Klartext zurückgegeben — nur `true/false`.

## Konfiguration ändern

```json
POST /tools/config_set
{"alert_webhook_url": "https://<deine-plattform>/incoming/abc123"}
```

```json
POST /tools/config_set
{"hook_secret": "<mindestens 16 Zeichen, z.B. openssl rand -hex 32>"}
```

```json
POST /tools/config_set {"default_base": "original"}
POST /tools/config_set {"clear": ["alert_webhook_url"]}
```

Regeln:

- `alert_webhook_url` muss mit `https://` beginnen
- `hook_secret` mindestens 16 Zeichen
- Änderungen greifen sofort, kein Redeploy
- `AIRTABLE_PAT` lässt sich hier **nicht** setzen — nur im Platform-Panel

## Hook testen (ohne zu schreiben)

```json
POST /tools/hook_test {"record_id": "rec…"}
```

Antwort enthält: Hook-URL, benötigte Header, Beispiel-Body, fertigen `curl`, Warnung falls kein Secret
gesetzt ist, und `would_do` — also was ein echter Aufruf auslösen würde.

```json
{"ok": true, "hook_url": "…/hooks/airtable", "secret_configured": false,
 "warning": "HOOK_SECRET ist nicht gesetzt — /hooks/airtable ist offen …",
 "sample_body": {"record_id": "rec…", "mode": "preview", "event": "Verbindungstest"},
 "would_do": {"mode": "preview", "planned": 0, "actions": []}}
```

Ablauf beim Anbinden: `hook_test` → in Airtable-Automation mit `mode=preview` aufrufen → Ergebnis
vergleichen → in der Automation auf `mode=apply` stellen.

## Base-Struktur erweitern

Alle drei Werkzeuge liefern **standardmäßig nur eine Vorschau** des Requests. Erst
`preview=false` **und** `confirm=true` sendet wirklich.

```json
POST /tools/field_create
{"table": "prijave", "name": "Rückruf notiert", "type": "singleSelect",
 "options": {"choices": [{"name": "ja"}, {"name": "nein"}]}}
```

```json
POST /tools/table_create
{"name": "Prüfliste", "fields": [{"name": "Name", "type": "singleLineText"},
                                 {"name": "Datum", "type": "date"}]}
```

```json
POST /tools/field_update
{"table": "prijave", "field_id": "fld…", "options": {"choices": [{"name": "Offen"}, {"name": "Erledigt"}]}}
```

Antwort im Vorschau-Modus:

```json
{"preview": true, "method": "POST", "url": "https://api.airtable.com/v0/meta/bases/…/fields",
 "payload": {"name": "Rückruf notiert", "type": "singleSelect", "choices": […]},
 "note": "Nichts gesendet. Zum Anlegen preview=false und confirm=true setzen."}
```

### Voraussetzung

Der Airtable-Schlüssel braucht dafür zusätzlich den Scope **`schema.bases:write`** und Zugriff auf die
Base. Ohne ihn antwortet der Dienst mit `Kein Zugriff …`. Nach dem Anlegen wird der Schema-Cache
automatisch verworfen.

### Grenzen

- Kein Löschen von Tabellen oder Feldern (absichtlich)
- Feldtypen lassen sich nicht umbauen, nur Name und Optionen
- Formeln, Rollups und Verknüpfungen legt man in der Airtable-Oberfläche an
