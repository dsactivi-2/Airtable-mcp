# Hermes — Werkzeugreferenz

Generiert aus `GET /schema/tools` am 1.5.5 (Stand: 2026-10-29). 31 Werkzeuge. Nicht von Hand pflegen — nach Änderungen neu erzeugen.

Quelle: `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7` · MCP: `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/`

## Lesen (9)

### `schema_get`

Tabellen, Felder, Typen und erlaubte Auswahlwerte einer Base (kopieren|original).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `include_choices` | boolean | nein | True | Auswahlwerte mitliefern |
| `refresh` | boolean | nein | False | Schema neu von Airtable laden |

### `candidates_search`

Kandidaten suchen über Name, Telefon (Handy oder Festnetz), Kundennummer oder Passnummer.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `query` | ? | nein | None | Freitext: Name, Kundennummer, Passnummer |
| `phone` | ? | nein | None | Handy- oder Festnetznummer, beliebiges Format |
| `status` | ? | nein | None | Status kandidata (exakt) |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `limit` | integer | nein | 25 | Treffer pro Seite |
| `offset` | integer | nein | 0 | Seiten-Offset |

### `applications_search`

Bewerbungen filtern nach Status, Casting-Gruppe/-Ausgang, Vertrag, Visum, Zeiträumen, überfälligen Aktionen und fehlenden Unterlagen.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `query` | ? | nein | None | Freitext über Name, Telefon, Kundennummer, Passnummer |
| `phone` | ? | nein | None | Telefonnummer in beliebigem Format |
| `status_kandidata` | ? | nein | None | Status kandidata exakt, z.B. Casting, Primljeni, Ugovor |
| `casting_grupa` | ? | nein | None | Casting-Gruppe: UJUTRO oder POPODNE |
| `casting_ishod` | ? | nein | None | Casting-Ergebnis, z.B. Došao, Prošao praktični |
| `ugovor_tok` | ? | nein | None | Vertragsstand: Priprema, Poslato kandidatu, Potpisan, Poslato nadležnima |
| `visa_ishod` | ? | nein | None | Visum-Ergebnis: Dopuna, Dobio vizu, Odbijenica |
| `casting_from` | ? | nein | None | Termin casting ab (YYYY-MM-DD) |
| `casting_to` | ? | nein | None | Termin casting bis (YYYY-MM-DD) |
| `action_due_before` | ? | nein | None | Rok akcije vor (YYYY-MM-DD) |
| `only_overdue` | boolean | nein | False | Nur überfällige Aktionen |
| `only_missing_documents` | boolean | nein | False | Nur unvollständige Unterlagen |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `sort_by` | string | nein | action_due | action_due / name / status / casting_date |
| `sort_dir` | string | nein | asc | Sortierrichtung |
| `limit` | integer | nein | 25 | Treffer pro Seite |
| `offset` | integer | nein | 0 | Seiten-Offset |

### `candidate_dossier`

Komplette Kandidatenakte als ein JSON: Stammdaten, Prozess, Termine, Dokumente, Bewertungen, Aufgaben, Vorab-Text für einen Anruf.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | ? | nein | None | Airtable-Datensatz-ID (rec…) |
| `query` | ? | nein | None | Alternativ: Name |
| `phone` | ? | nein | None | Alternativ: Telefonnummer |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `application_get`

Eine Bewerbung mit allen Feldern und Dokumenten.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | string | ja | — | Airtable-Datensatz-ID (rec…) |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `documents_list`

Hinterlegte Dateien eines Kandidaten mit Name, Typ, Größe und Link.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | string | ja | — | Airtable-Datensatz-ID (rec…) |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `casting_ratings_list`

Casting-Bewertungen, optional nur für einen Kandidaten.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `candidate_record_id` | ? | nein | None | Nur Bewertungen dieses Kandidaten |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `limit` | integer | nein | 50 | Maximale Anzahl |

### `pipeline_summary`

Übersicht: Anzahl je Status, überfällige Aktionen, fehlende Unterlagen, Termine der nächsten 7 Tage.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `due_report`

Tagesbericht: fällige und überfällige Aktionen, Casting- und Visumtermine, fehlende Unterlagen.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `days_ahead` | integer | nein | 7 | Termine der nächsten X Tage |

## Schreiben (7)

### `application_create`

Neue Bewerbung anlegen (mindestens 'Ime i prezime'); prüft vorher auf gleiche Telefonnummer und legt nur mit allow_duplicate=true trotzdem an.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `fields` | object | ja | — | Felder des neuen Datensatzes; 'Ime i prezime' ist Pflicht |
| `note` | ? | nein | None | Optionaler Startvermerk in 'Bilješka' |
| `allow_duplicate` | boolean | nein | False | true = trotz gleicher Telefonnummer anlegen |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `application_update`

Freigegebene Felder einer Bewerbung setzen; optional mit Protokoll-Notiz.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | string | ja | — | Airtable-Datensatz-ID (rec…) |
| `fields` | object | ja | — | Zu setzende Felder (nur freigegebene) |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `note` | ? | nein | None | Optionaler Protokoll-Eintrag |

### `applications_bulk_update`

Mehrere Kandidaten gleichzeitig ändern — standardmäßig nur Vorschau, Schreiben erst mit dry_run=false und confirm=true, maximal 50 Datensätze.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `fields` | object | ja | — | Zu setzende Felder für alle Treffer |
| `record_ids` | ? | nein | None | Explizite Datensatz-IDs |
| `filter` | ? | nein | None | Filter wie bei applications_search |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `limit` | integer | nein | 50 | Maximal 50 Datensätze pro Aufruf |
| `dry_run` | boolean | nein | True | true = nur Vorschau |
| `confirm` | boolean | nein | False | Muss true sein, damit geschrieben wird |

### `application_add_note`

Notiz mit Zeitstempel und Verfasser anhängen (bestehende Notizen bleiben erhalten).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | string | ja | — | Airtable-Datensatz-ID (rec…) |
| `note` | string | ja | — | Notiztext |
| `author` | string | nein | agent | Verfasser, erscheint in der Notiz |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `casting_rating_upsert`

Casting-Bewertung anlegen oder aktualisieren, inklusive Verknüpfung zum Kandidaten.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `fields` | object | nein | — | Bewertungsfelder |
| `rating_id` | ? | nein | None | Vorhandene Bewertung aktualisieren |
| `candidate_record_id` | ? | nein | None | Kandidat verknüpfen |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `document_upload`

Datei in ein Anhang-Feld hochladen (pdf, jpg, jpeg, png, doc, docx, max. 10 MB).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | string | ja | — | Airtable-Datensatz-ID (rec…) |
| `field` | string | ja | — | Anhang-Feld, z.B. Lebenslauf |
| `file` | string | ja | — | Datei (pdf, jpg, jpeg, png, doc, docx) — Adresse des Datei-Uploaders |
| `filename` | ? | nein | None | Dateiname mit Endung; sonst aus der Datei abgeleitet |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `note` | ? | nein | None | Optionaler Eintrag in 'Bemerkung zu Dokumenten' |

### `tasks_manage`

Aufgaben in Table 1 lesen, anlegen oder Status setzen.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `action` | string | nein | list | list, create oder update |
| `task_id` | ? | nein | None | rec… für update |
| `name` | ? | nein | None | Aufgabentitel |
| `notes` | ? | nein | None | Beschreibung der Aufgabe |
| `status` | ? | nein | None | Aufgabenstatus |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `limit` | integer | nein | 25 | Treffer pro Seite |

## Automatik (3)

### `automation_rules`

Automatik-Regeln ansehen oder ändern.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `action` | string | nein | get | get = Regeln ansehen, set = Regeln überschreiben |
| `rules` | ? | nein | None | Regeln (nur bei action=set) |

### `automation_run`

Automatik ausführen — preview zeigt nur den Plan, apply schreibt Änderungen und Aufgaben.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `mode` | string | nein | preview | preview = nur zeigen, apply = schreiben |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `limit` | integer | nein | 300 | Maximale Anzahl Datensätze |
| `record_ids` | ? | nein | None | Optional nur diese Datensätze prüfen (z.B. für einen Testlauf) |

### `automation_log`

Protokoll der Automatik und der Massenänderungen.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `limit` | integer | nein | 25 | Anzahl Einträge |

## Betrieb (9)

### `audit_list`

Verlauf: wer wann welches Werkzeug auf welchem Datensatz ausgeführt hat (filterbar nach Werkzeug, Datensatz, Aufrufer).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `limit` | integer | nein | 50 | Anzahl Einträge |
| `tool` | ? | nein | None | Nur Einträge dieses Werkzeugs |
| `record_id` | ? | nein | None | Nur Einträge zu diesem Datensatz |
| `actor` | ? | nein | None | Nur Einträge dieses Aufrufers |

### `error_log`

Fehlerprotokoll: fehlgeschlagene Aufrufe mit Zeitpunkt, Werkzeug, Aufrufer und Ursache.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `limit` | integer | nein | 50 | Anzahl Einträge |

### `alerts_list`

Gespeicherte Alarme (Fehler, Datenauffälligkeiten) und ob ein Alarm-Webhook konfiguriert ist.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `limit` | integer | nein | 50 | Anzahl Einträge |

### `data_health`

Qualitätsprüfung: Datensätze ohne Status, ohne nächste Aktion, überfällig, mit fehlenden Unterlagen, verpassten Terminen oder doppelten Telefonnummern.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `notify` | boolean | nein | False | true = Auffälligkeiten als Alarm melden |
| `limit` | integer | nein | 20 | Beispiele pro Kategorie |

### `hook_test`

Testet die Anbindung an Airtable-Automationen: zeigt Hook-URL, Header und was ein Aufruf auslösen würde — ohne etwas zu schreiben.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `record_id` | ? | nein | None | Datensatz für den Test (optional) |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |

### `config_get`

Aktuelle Konfiguration anzeigen: Standard-Base, ob Alarm-Webhook und Hook-Secret gesetzt sind.

Keine Parameter.

### `config_set`

Konfiguration ändern: Alarm-Webhook, Hook-Secret, Standard-Base — wirkt sofort, ohne Redeploy.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `alert_webhook_url` | ? | nein | None | HTTPS-Adresse für Alarme |
| `hook_secret` | ? | nein | None | Gemeinsames Passwort für /hooks/airtable |
| `default_base` | ? | nein | None | Base, wenn ein Aufruf keine nennt |
| `clear` | ? | nein | None | Schlüssel entfernen, z.B. ['alert_webhook_url'] |

### `service_info`

Version, Werkzeugliste, Änderungsverlauf und die Zuständigkeit für die drei Secrets (AIRTABLE_PAT, HOOK_SECRET, ALERT_WEBHOOK_URL). Nach jedem Verbinden einmal aufrufen.

Keine Parameter.

### `schedule_sync`

Stellt den Tagesplan auf den aktuellen Sommer-/Winterwert um (Sommerzeit 05:00 UTC, Winterzeit 06:00 UTC = 07:00 Ortszeit). Täglich aufrufen, ist idempotent.

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `request_id` | ? | nein | None | Request-ID des Tageslaufs (nur beim ersten Mal nötig) |
| `apply` | boolean | nein | True | false = nur anzeigen, welcher Cron gelten müsste |

## Struktur (3)

### `table_create`

Neue Tabelle in der Base anlegen (Vorschau zuerst, echtes Anlegen nur mit confirm).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `name` | string | ja | — | Name der neuen Tabelle |
| `fields` | array | ja | — | Felder: [{"name": "Name", "type": "singleLineText"}] |
| `description` | ? | nein | None | Beschreibung der Tabelle |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `preview` | boolean | nein | True | true = nur zeigen, was gesendet würde |
| `confirm` | boolean | nein | False | Muss true sein, damit die Tabelle entsteht |

### `field_create`

Neues Feld in einer Tabelle anlegen (Vorschau zuerst, echtes Anlegen nur mit confirm).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `table` | string | ja | — | Tabellenname oder Schlüssel (prijave, casting, tasks) |
| `name` | string | ja | — | Feldname |
| `type` | string | ja | — | Airtable-Feldtyp, z.B. singleLineText, singleSelect, date, number |
| `options` | ? | nein | None | Optionen, z.B. choices für singleSelect |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `preview` | boolean | nein | True | true = nur zeigen, was gesendet würde |
| `confirm` | boolean | nein | False | Muss true sein, damit wirklich geschrieben wird |

### `field_update`

Feld umbenennen oder Auswahlwerte ändern (Vorschau zuerst, echte Änderung nur mit confirm).

| Parameter | Typ | Pflicht | Standard | Beschreibung |
|---|---|---|---|---|
| `table` | string | ja | — | Tabellenname oder Schlüssel |
| `field_id` | string | ja | — | Feld-ID fld… |
| `name` | ? | nein | None | Neuer Name |
| `options` | ? | nein | None | Neue Optionen (z.B. choices) |
| `base` | string | nein | kopieren | Base: kopieren (Standard) oder original |
| `preview` | boolean | nein | True | true = nur zeigen, was gesendet würde |
| `confirm` | boolean | nein | False | Muss true sein, damit wirklich geschrieben wird |
