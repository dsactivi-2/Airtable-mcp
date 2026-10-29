# Tags, Prozessstufen und was automatisch passiert

## Das Grundmuster

Jede Prozessstufe hat **drei** Begleiter:

| Typ | Beispiel | Wer setzt es |
|---|---|---|
| `Status kandidata` (Single-Select) | `Casting` | Der Agent — das ist der Führungsstatus |
| Tags der Stufe (Multi-Select) | `Tagovi casting`, `CASTING` | Der Agent, sobald ein Ereignis eintritt |
| Freitextfelder | `Sljedeća akcija`, `Rok akcije`, `Bilješka` | Der Agent |

Der Status ist die Wahrheit. Tags sind die Feinkörnung innerhalb der Stufe. **Nie** ein Tag setzen, ohne
den Status passend zu führen — sonst widersprechen sich Status und Tags.

## Stufe → Tags

| Status | Tag-Felder | Werte | Wann setzen |
|---|---|---|---|
| `Zainteresiran` | `Zainteresiranost kandidata`, `Tagovi zainteresiran` | `PRISTAO`, `POPUNI CV` / `POPUNITI CV` | Kandidat hat zugesagt bzw. CV angefordert |
| `Zeleni / obrada` | `Dok. obrada`, `Dokumenti` | `DIPLOMA`, `SVJEDOČANSTVO 1–4`, `SLIKA PASOŠA`, `FOTOGRAFIJA ZA CV` | Unterlage liegt vor bzw. geprüft |
| `Pre-casting` | `Tagovi pre-casting`, `PRIPREMA ZA CASTING` | `PROVJERA CV`, `PRECASTING CALL`, `KONTAKT 5 DANA PRIJE CASTINGA`, `KONTAKT 2 DANA PRIJE CASTINGA` | CV geprüft, Telefoninterview geführt, Erinnerung verschickt |
| `Casting` | `Tagovi casting`, `CASTING` | `KONTAKT NA DAN CASTINGA`, `DOLAZI`, `NE DOLAZI`, `DOŠAO`, `NIJE DOŠAO`, `PROŠAO PRAKTIČNI`, `NIJE PROŠAO PRAKTIČNI`, `USMENI PROŠAO`, `USMENI NIJE PROŠAO` | Einladung, Zusage, Erscheinen, Ergebnis — je Ereignis genau ein Tag |
| `Primljeni` | `Tagovi primljen` | `SPREMAN ZA UGOVOR` | Casting bestanden, Unterlagen vollständig |
| `Ugovor` | `Tagovi ugovor`, `UGOVOR` | `UGOVOR`, `IZJAVA O RADU`, `POSLATO KANDIDATU`, `POTPISAN`, `POSLATO NADLEŽNIMA` | Vertrag erstellt, versendet, unterzeichnet, weitergeleitet |
| `Predsaglasnost` | `Tagovi predsaglasnost`, `PREDSAGLASNOT` | `POSLODAVAC PREDAO ZAHTJEV`, `STIGLA PREDSAGLASNOST` | Arbeitgeber hat beantragt / Zustimmung liegt vor |
| `Slanje potpisanih ugovora` | `Tagovi ugovor` | `POTPISAN`, `POSLATO NADLEŽNIMA` | Nachweise an Behörde |
| `Viziranje` | `Tagovi viziranje`, `VIZIRANJE` | `PROVJERA FINANCIJA`, `REZERVACIJA TERMINA`, `UPLATA TERMINA`, `VIDEX`, `POTVRDA TERMINA`, `FOTOGRAFIJE`, `PASOŠ`, `UGOVOR O RADU`, `PREDSAGLASNOST`, `IZJAVA O ZAPOSLENJU`, `DOKAZ O UPLATI`, `KONTAKT 2 DANA PRIJE TERMINA ZA VIZU`, `KONTAKT NA DAN TERMINA ZA VIZU`, `PREDAO ZAHTJEV ZA VIZU` | Vorbereitung des Visumtermins, Schritt für Schritt |
| `Čekanje vize` | `Tagovi čekanje vize`, `ČEKANJE VIZE` | `ODBIJENICA`, `DOPUNA`, `DOBIO VIZU` | Ergebnis der Botschaft |
| `Čeka početak rada` | `Tagovi početak rada` | `SMJEŠTAJ`, `ADRESA RADA`, `DOČEK`, `PRIJAVA ADRESE`, `POČEO SA RADOM` | Organisation vor der Einreise |
| `ODBIJEN` / `Odustao` | `Razlog izlaza` (Single-Select) | `Casting`, `Dokumenti`, `Viza`, `Odustao kandidat`, `Ostalo` | Abschluss mit Begründung — Status **und** Grund setzen |

### Zwei parallele Tag-Familien

Es gibt denselben Inhalt zweimal: einmal GROSS (`CASTING`, `VIZIRANJE`, `UGOVOR`, `PREDSAGLASNOT`) und
einmal als `Tagovi …` (`Tagovi casting`, `Tagovi viziranje` …). Das ist historisch gewachsen.

**Regel:** Die `Tagovi …`-Felder führen, die GROSS-Felder nur füllen, wenn der Nutzer es verlangt.
Nicht doppelt setzen — sonst widersprechen sich die Ansichten.

## Was Airtable automatisch berechnet (Agent kann es nicht schreiben)

| Feld | Verhalten |
|---|---|
| `Obrazovanje (norm.)` | Formel: `Obrazovanje ili iskustvo` → `Da` / `Ne` / `Nepoznato` |
| `Njemački (samoprocjena)` | Formel: `Poznavanje njemačkog jezika` → `NE` / `OSNOVE` / `DA` / `Nepoznato` |
| `Vozačka (kategorija)` | Formel: `Vozačka dozvola` → Großbuchstaben, leer = `Nepoznato` |
| `Test oznaka (po imenu)` | Formel: markiert Datensätze, deren Name „test“ enthält |
| `Casting ocjene` (Verknüpfung) | entsteht durch Anlegen einer Bewertung, nicht durch Schreiben ins Feld |
| `Attachments` / `Attachment Summary` (Table 1) | Anhang wird von Airtable zusammengefasst, nicht vom Agenten |

**Wichtig:** Diese Felder sind Anzeige, keine Eingabe. Wer sie beschreiben will, ändert das **Quellfeld**
(`Obrazovanje ili iskustvo`, `Poznavanje njemačkog jezika`, `Vozačka dozvola`) — dann rechnet Airtable neu.

## Was der Dienst selbst berechnet (nicht gespeichert, nur in Antworten)

`missing_documents` (fehlende Pflichtunterlagen für den aktuellen Status), `overdue` (Frist überschritten,
Status nicht final), `pre_call_brief` (fertiger Sprechzettel), `days`-Vergleiche für Termine.

Pflichtunterlagen, sobald der Status über `Zeleni / obrada` hinaus ist: `DIPLOMA`, `SLIKA PASOŠA`,
`FOTOGRAFIJA ZA CV` im Feld `Dokumenti`.

## Trigger: was lädt automatisch, was nicht

| Auslöser | Lädt automatisch? |
|---|---|
| Formeln und Verknüpfungen (siehe oben) | ja, sofort beim Speichern |
| KI-Feld `Attachment Summary` in Table 1 | ja, sobald eine Datei im Feld `Attachments` liegt |
| Tag-Felder | **nein** — müssen gesetzt werden, sonst bleiben sie leer |
| `Status` (einfaches Textfeld im Altbestand) | **nein** — wird nicht aus `Status kandidata` mitgeschrieben |
| `Sljedeća akcija` / `Rok akcije` | **nein** — nur durch Agent oder Automatik-Regel |
| Tagesbericht und Folgeaufgaben | ja, täglich 07:00 durch die Automatik (aktuell Vorschau-Modus) |
| Reaktion auf eine Änderung in Sekunden | **nein** — dafür gibt es noch keinen Webhook (siehe good-to-have) |
