# Automatik

## Was läuft

Täglich 06:00 UTC (= 07:00 Europe/Berlin bzw. Sarajevo in der Winterzeit, 08:00 in der Sommerzeit) prüft der Dienst alle Bewerbungen **und schreibt** (aktiv):

1. **Tagesbericht** — überfällige Aktionen, Casting- und Visumtermine der nächsten 7 Tage, fehlende Unterlagen
2. **Regeln** — Statuswechsel und nahende Termine erzeugen Folgeaufgaben

Zwei Modi:

- `preview` — zeigt nur den Plan, schreibt nichts (aktuell aktiv)
- `apply` — schreibt Felder, Notizen und Aufgaben, protokolliert alles

## Sommer-/Winterzeit

`schedule_sync` prüft die Zeitzone (Europe/Berlin/Sarajevo) und stellt den Tagesplan auf
`cron(0 5 * * ? *)` (Sommer) bzw. `cron(0 6 * * ? *)` (Winter) um. Ein eigener Zeitplan ruft es
täglich um 03:00 UTC auf — idempotent, ändert also nur, wenn der Wert abweicht.

## Regeln (Standard)

| ID | Auslöser | Wirkung |
|---|---|---|
| `status_casting` | Status = `Casting` | Aufgabe „Einladung + Termin bestätigen“, nächste Aktion, Frist +2 Tage |
| `status_primljeni` | Status = `Primljeni` | Aufgabe „Unterlagen prüfen“, Frist +3 Tage |
| `status_ugovor` | Status = `Ugovor` | Aufgabe „Vertrag versenden“, Frist +3 Tage |
| `status_viziranje` | Status = `Viziranje` | Aufgabe „Visumsunterlagen prüfen“, Frist +5 Tage |
| `appointment_2d` | `Termin casting` in ≤ 2 Tagen | Aufgabe „Kandidat erinnern“ |

Regeln lesen und ändern:

```json
POST /tools/automation_rules
{"action": "get"}
```
```json
POST /tools/automation_rules
{"action": "set", "rules": [{"id": "status_casting", "kind": "status", "status": "Casting",
  "task": "Einladung + Termin bestätigen", "next_action": "Termin bestätigen", "due_days": 2}]}
```

Regel-Felder: `id`, `kind` (`status` oder `appointment`), `status` bzw. `field` + `days_before`,
`task`, `next_action`, `due_days`.

## Sicherheitsnetze

- **Genau einmal pro Datensatz:** jeder Regel-Lauf setzt einen Marker (180 Tage). Kein doppelter Task.
- **Vorschau zuerst:** `automation_run` mit `mode=preview` zeigt jede geplante Aktion mit Name und Frist.
- **Testlauf auf einem Datensatz:** `record_ids` einschränken, z. B. `{"mode": "apply", "record_ids": ["rec..."]}`
- **Protokoll:** `automation_log` zeigt jede Automatik-Aktion und jede Massenänderung mit Zeitstempel.
- **Notizspur:** jede Automatik-Aktion hinterlässt eine Zeile in `Bilješka` mit `[automatisch]`.

## Grenzen

- Die Automatik ersetzt **keine** Zustellung. E-Mail, Viber, Facebook Messenger und SMS verschickt die
  eigene Plattform; der Dienst liefert `report_text` und die Aktionsliste.
- Kein Löschen, kein Rückgängigmachen. Änderungen werden nur durch erneutes Setzen korrigiert.


## Protokoll, Fehler und Alarme

| Werkzeug | Inhalt |
|---|---|
| `audit_list` | wer wann was: Werkzeug, Aufrufer, Datensatz, Felder, Dauer |
| `error_log` | fehlgeschlagene Aufrufe mit Ursache und Status |
| `alerts_list` | gespeicherte Alarme, zeigt ob ein Alarm-Webhook konfiguriert ist |
| `data_health` | Lücken und Fehler: ohne Status, ohne nächste Aktion, überfällig, fehlende Unterlagen, verpasste Termine, doppelte Nummern |

Aufrufer: Header `X-Actor` oder `X-Client`; ohne Header die Aufrufer-ID der Plattform.
Alarme werden immer gespeichert. Erst `ALERT_WEBHOOK_URL` macht daraus eine Push-Meldung.

## Anbindung an Airtable Automation

`POST /hooks/airtable` mit `{"record_id": "rec...", "mode": "apply", "event": "..."}`.
Mit `HOOK_SECRET` ist das Feld `hook_secret` im JSON-Body Pflicht (Header entfernt das Gateway). `mode=preview` schreibt nichts — gut zum Testen.
