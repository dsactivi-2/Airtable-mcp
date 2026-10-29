# Automatik

## Was läuft

Täglich 07:00 (Europe/Sarajevo) prüft der Dienst alle Bewerbungen:

1. **Tagesbericht** — überfällige Aktionen, Casting- und Visumtermine der nächsten 7 Tage, fehlende Unterlagen
2. **Regeln** — Statuswechsel und nahende Termine erzeugen Folgeaufgaben

Zwei Modi:

- `preview` — zeigt nur den Plan, schreibt nichts (aktuell aktiv)
- `apply` — schreibt Felder, Notizen und Aufgaben, protokolliert alles

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
