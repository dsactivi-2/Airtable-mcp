# Filtern und Suchen

Alle Aufrufe sind reines JSON. Jede Antwort hat `success` und ein `result`-Objekt.

## Kandidaten finden (`candidates_search`)

| Feld | Bedeutung |
|---|---|
| `query` | Freitext über Name, Kundennummer, Passnummer, Telefon, Notiz |
| `phone` | Telefonnummer in **jedem** Format — der Dienst normalisiert auf Ziffern und vergleicht die letzten 9 Stellen |
| `status` | Status kandidata exakt |
| `limit`, `offset` | Seitengröße (1–100), Offset für die nächste Seite |
| `base` | `kopieren` (Standard) oder `original` |

Telefon normalisiert: `+387 61 614 368`, `0038761614368`, `061 614 368` treffen denselben Kandidaten.
Festnetz funktioniert über `Pozivni broj` + `Broj telefona` zusammen.

## Bewerbungen filtern (`applications_search`)

| Parameter | Wirkung |
|---|---|
| `status_kandidata` | exakt, z. B. `Zainteresiran`, `Casting`, `Primljeni`, `Ugovor`, `Viziranje`, `Čekanje vize`, `ODBIJEN`, `Odustao` |
| `casting_grupa` | `UJUTRO` oder `POPODNE` |
| `casting_ishod` | `Dolazi`, `Došao`, `Nije došao`, `Prošao praktični`, `Usmeni prošao`, … |
| `ugovor_tok` | `Priprema`, `Poslato kandidatu`, `Potpisan`, `Poslato nadležnima` |
| `visa_ishod` | `Dopuna`, `Dobio vizu`, `Odbijenica` |
| `casting_from` / `casting_to` | Termin casting im Zeitraum (YYYY-MM-DD) |
| `action_due_before` | Rok akcije vor diesem Datum |
| `only_overdue` | nur überfällige Aktionen (Rok akcije < heute, Status nicht final) |
| `only_missing_documents` | nur unvollständige Unterlagen |
| `query` | Freitext wie oben |
| `sort_by` / `sort_dir` | `action_due`, `name`, `status`, `casting_date` · `asc`/`desc` |
| `limit` / `offset` | Paginierung |

**Finale Status** (zählen nie als überfällig): `Počeo sa radom `, `ODBIJEN`, `Odustao`.

## Typische Abfragen

```json
{"only_overdue": true, "sort_by": "action_due", "sort_dir": "asc"}
```
```json
{"casting_from": "2026-11-01", "casting_to": "2026-11-07", "casting_grupa": "UJUTRO"}
```
```json
{"status_kandidata": "Primljeni", "only_missing_documents": true}
```
```json
{"status_kandidata": "Ugovor", "action_due_before": "2026-10-31"}
```

## Übersichten statt Listen

`pipeline_summary` liefert Zählungen je Status, überfällige Aktionen, fehlende Unterlagen und die
Termine der nächsten 7 Tage. `due_report` liefert dieselbe Logik plus fertigen Berichtstext
(`report_text`) — ideal zum Weiterleiten an Mail, Viber oder Messenger.

## Massenänderung (`applications_bulk_update`)

```json
{"fields": {"Sljedeća akcija": "Unterlagen anfordern"},
 "filter": {"status_kandidata": "Primljeni", "only_missing_documents": true},
 "dry_run": true, "limit": 50}
```

Immer zuerst `dry_run=true`, Ergebnis prüfen, dann `dry_run=false` **und** `confirm=true`.
Ohne `confirm=true` wird nichts geschrieben. Ohne `record_ids` **oder** `filter` bricht der Dienst ab.

## Fehlermeldungen richtig lesen

| Meldung | Bedeutung |
|---|---|
| `Nicht schreibbare Felder in Prijave (test): …` | Feld ist Formel/Verknüpfung/Anhang — die erlaubten Felder stehen in der Meldung |
| `Ungültiger Wert für 'Status kandidata': …` | Tippfehler oder alte Option — die erlaubten Werte stehen in der Meldung |
| `Kein Zugriff auf diese Airtable-Base` | Base fehlt im Airtable-Token unter Access |
| `Kein Kandidat gefunden` | Suche zu eng — mit Telefonnummer oder Nachnamen erneut versuchen |
