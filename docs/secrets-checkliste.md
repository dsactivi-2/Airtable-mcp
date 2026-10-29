# Secrets-Checkliste

Stand: Version 1.5.1 · drei Variablen, mehr nicht.

## Aktueller Zustand

| Secret | Gesetzt | Wer trägt es ein | Wo |
|---|---|---|---|
| `AIRTABLE_PAT` | **ja** | Kontoinhaber (Mensch) | CodeWords → Projekt → Integrations-Panel |
| `HOOK_SECRET` | **ja** | Mensch legt Wert fest (Agent darf setzen) | `config_set` oder Panel — Aufruf erfolgt über das Feld `hook_secret` im JSON-Body |
| `ALERT_WEBHOOK_URL` | nein | Mensch besorgt die Adresse | `config_set` oder Panel |

Abfragen mit `POST /tools/service_info` → Abschnitt `secrets` zeigt je `configured: true/false`.

## Woher kommen die Werte?

### `AIRTABLE_PAT` — aus Airtable

1. airtable.com → Konto → **Developer hub** → **Personal access tokens** → *Create new token*
2. Scopes: `data.records:read`, `data.records:write`, `schema.bases:read`
   (für Tabellen/Felder anlegen zusätzlich `schema.bases:write`)
3. Unter **Access**: *Ilvana i Hase (Kopieren)* und *Ilvana i Hase*
4. Wert beginnt mit `pat…` → ins Integrations-Panel

### `HOOK_SECRET` — selbst erzeugen

Kein Anbieter. Mindestens 16 Zeichen, empfohlen 32+:

```bash
openssl rand -hex 32            # macOS / Linux
[guid]::NewGuid().ToString('N') # Windows PowerShell (32 Zeichen)
```

Eintragen an **zwei** Stellen, identisch:

1. Dienst: `config_set {"hook_secret": "<wert>"}` oder Panel
2. Airtable-Automation: Feld `hook_secret` im JSON-Body

**Wichtig:** Der Header `X-Hook-Secret` wird vom Gateway entfernt — das Secret muss im Body stehen.

Wenn der Agent das Secret setzt, kann er es danach nicht mehr auslesen (nur `true/false`).
Wert vorher notieren oder selbst im Panel eintragen.

### `ALERT_WEBHOOK_URL` — von der Empfängerseite

Eine Adresse, die `POST` mit JSON annimmt:

| Empfänger | Fundort |
|---|---|
| n8n | Node „Webhook" → Production-URL |
| Make / Zapier | „Custom Webhook" → angezeigte URL |
| eigene Plattform | eigener Empfänger-Endpunkt, z. B. `https://runtime.codewords.ai/run/<service_id>/` |
| eigenes Backend | selbst angelegter Endpunkt |

Erwartetes JSON:

```json
{"service":"ilvana-airtable","at":"2026-10-29 05:26","kind":"tool_error",
 "message":"…","details":{"tool":"…"},"actor":"…"}
```

`kind`: `tool_error`, `tool_crash`, `validation_error`, `data_health`.

Ohne URL gehen Alarme nicht verloren — sie liegen in `alerts_list` (`webhook_configured: false`).

## Wechseln

```json
POST /tools/config_set {"hook_secret": "<neu>"}
POST /tools/config_set {"alert_webhook_url": "https://…"}
POST /tools/config_set {"clear": ["alert_webhook_url"]}
```

`AIRTABLE_PAT` nur im Panel. Nach jedem Wechsel: `service_info` und `hook_test` prüfen.

## Prüfen

```bash
curl -X POST https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/hooks/airtable \
  -H 'Authorization: Bearer <CODEWORDS_API_KEY>' -H 'Content-Type: application/json' \
  -d '{"record_id":"rec…","mode":"preview","hook_secret":"<wert>"}'
```

- `200` → Secret stimmt
- `401` → Secret fehlt oder weicht ab


## Anforderungen an den Empfänger

Der Dienst schickt `POST` mit `Content-Type: application/json` und **ohne** Auth-Header.

| Anforderung | Warum |
|---|---|
| nimmt `POST` mit JSON an | der Alarm ist ein JSON-Objekt |
| antwortet mit `2xx` | alles andere wird als Fehlschlag protokolliert (`alerts_list` zeigt es) |
| ist öffentlich erreichbar | kein Auth-Header, kein Signaturverfahren |
| **kein** CodeWords-Runtime-Endpunkt (`…/run/…`) | der verlangt einen Bearer-Key, den der Alarm nicht mitschickt → 401 |

### Selbsttest vor dem Eintragen

```bash
curl -i -X POST "<DEINE_URL>" -H 'Content-Type: application/json' \
  -d '{"service":"ilvana-airtable","kind":"tool_error","message":"Test"}'
```

`200` → passt. Alles andere → Adresse oder Methode prüfen.

### Wo die Adresse herkommt

| Empfänger | Fundort |
|---|---|
| n8n | Node *Webhook* → Production-URL (nach Aktivierung) |
| Make | *Webhooks → Custom webhook* → „Address" |
| Zapier | *Webhooks by Zapier → Catch Hook* → angezeigte URL |
| eigener Server | eigener Endpunkt, z. B. `https://deine-domain.de/alerts/ilvana` |
| nur zum Testen | webhook.site — öffentlich lesbar, nicht dauerhaft nutzen |

### Wenn der Alarm ankommt

Der Dienst schickt dieses Objekt:

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

`kind` ist einer von `tool_error`, `tool_crash`, `validation_error`, `data_health`.
