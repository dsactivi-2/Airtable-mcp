# Schreiben: anlegen, ändern, hochladen

Alle Schreibaufrufe laufen über freigegebene Felder. Was nicht schreibbar ist (Formeln, Verknüpfungen,
Anhänge), lehnt der Dienst mit der Liste der erlaubten Felder ab.

## Neue Bewerbung anlegen

```json
POST /tools/application_create
{
  "fields": {
    "Ime i prezime": "Amar Bitići",
    "Ime": "Amar",
    "Prezime": "Bitići",
    "Pozivni broj": "+387",
    "Broj telefona": "061468027",
    "Status kandidata": "Zainteresiran"
  },
  "note": "Bewerbung per Telefon aufgenommen"
}
```

Regeln:

- `Ime i prezime` ist **Pflicht** — das ist das Primärfeld.
- **Dubletten-Schutz:** existiert die Telefonnummer (`Pozivni broj` + `Broj telefona`, normalisiert)
  bereits, antwortet der Dienst mit **409** und nennt Name und Record-ID des Treffers. Nur mit
  `allow_duplicate: true` wird trotzdem angelegt.
- `note` landet als datierte Zeile in `Bilješka`.
- Antwort enthält `record_id` und eine Kurzfassung (`summary`).

## Ändern

```json
POST /tools/application_update
{"record_id": "rec…", "fields": {"Status kandidata": "Primljeni"}, "note": "Casting bestanden"}
```

Nur übergebene Felder werden geändert. Nicht schreibbar: `Obrazovanje (norm.)`, `Njemački (samoprocjena)`,
`Vozačka (kategorija)`, `Test oznaka (po imenu)`, `Casting ocjene` sowie alle Anhang-Felder.

## Massenänderung

```json
POST /tools/applications_bulk_update
{"fields": {"Sljedeća akcija": "Unterlagen anfordern"},
 "filter": {"status_kandidata": "Primljeni", "only_missing_documents": true},
 "dry_run": true, "limit": 50}
```

Zuerst `dry_run=true` prüfen, dann `dry_run=false` **und** `confirm=true`. Ohne beide Flags wird nichts
geschrieben, maximal 50 Datensätze pro Aufruf.

## Notizen

```json
POST /tools/application_add_note
{"record_id": "rec…", "note": "Rückruf vereinbart", "author": "Amir"}
```

Wird angehängt, nie überschrieben; jede Zeile bekommt Zeitstempel und Verfasser.

## Casting-Bewertung

```json
POST /tools/casting_rating_upsert
{"candidate_record_id": "rec…", "fields": {"Termin casting": "2026-10-29", "Grupa": "UJUTRO",
 "Stručnost (1-5)": 4, "Ocjenjivač": "Amir", "Datum ocjene": "2026-10-29"}}
```

Ohne `rating_id` wird eine neue Bewertung angelegt, mit `rating_id` eine bestehende ergänzt.

## Dateien hochladen

```json
POST /tools/document_upload
{"record_id": "rec…", "field": "Lebenslauf", "file": "https://…/cv.pdf",
 "filename": "cv.pdf", "note": "Lebenslauf, 2 Seiten"}
```

- Felder: `Lebenslauf`, `Reisepass`, `Führerschein`, `Zeugnisse`, `Foto`, `Sonstige Dokumente`
  (in Table 1 zusätzlich `Attachments`)
- Erlaubt: PDF, JPG, JPEG, PNG, DOC, DOCX — maximal 10 MB
- `file` ist eine Adresse; `data:`-URIs (Base64) werden ebenfalls akzeptiert
- Vorhandene Anhänge bleiben erhalten, der neue wird ergänzt

## Aufgaben

```json
POST /tools/tasks_manage {"action": "create", "name": "Unterlagen prüfen", "notes": "bis Freitag"}
POST /tools/tasks_manage {"action": "update", "task_id": "rec…", "status": "Done"}
```

## Was nicht geht

- Löschen von Datensätzen, Dateien, Tabellen oder Feldern
- Anhänge über `application_update` setzen (dafür `document_upload`)
- Felder, die Airtable berechnet
