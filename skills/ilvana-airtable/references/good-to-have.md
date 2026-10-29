# Was noch sinnvoll wäre

Nach Wirkung sortiert. Jeder Punkt ist klein genug für einen einzelnen Arbeitsschritt.

## Sofort spürbar

1. **Webhook statt Tageslauf.** Airtable-Automation oder die eigene Plattform meldet jede Änderung sofort
   an einen Endpunkt; Reaktion in Sekunden statt am nächsten Morgen. Voraussetzung für zeitkritische
   Casting-Einladungen.
2. **Automatik auf `apply` schalten** — sobald die Regeln fachlich bestätigt sind.
3. **Zustellung anbinden.** `report_text` per Mail, Viber oder Messenger an das Team; heute muss es
   jemand abrufen.
4. **Doppelten-Erkennung** beim Anlegen: gleiche Telefonnummer oder gleicher Pass → warnen statt doppelt
   anlegen.

## Datenqualität

5. **Tag-Familien zusammenführen** (GROSS vs. `Tagovi …`). Aktuell wird derselbe Sachverhalt zweimal gepflegt.
6. **Feld `Status` (Text, Altbestand) abschaffen** — er läuft neben `Status kandidata` und wird nie
   automatisch gefüllt.
7. **Telefonnummern auf E.164 normalisieren** (`+387…`) — die Suche verzeiht viel, die Anzeige nicht.
8. **Pflichtfeld-Regel pro Stufe:** `Primljeni` ohne `DIPLOMA`, `SLIKA PASOŠA`, `FOTOGRAFIJA ZA CV` sollte
   nicht möglich sein.
9. **Trailing Space in `Počeo sa radom `** entfernen — der Wert hat ein Leerzeichen am Ende und bricht
   jeden naiven Vergleich.

## Prozess

10. **Verweildauer je Stufe** messen (seit wann `Viziranje`?) und im Tagesbericht melden, wenn eine Stufe
    zu lange hängt.
11. **Termin-Erinnerungen gestaffelt** (7/2/0 Tage) für Casting **und** Visum — heute nur Casting.
12. **Wiederherstellung nach Absage:** `Razlog izlaza` auswerten, um Ablehnungsgründe zu erkennen.
13. **Sammel-Import** aus Excel mit Vorschau und Dublettencheck, statt Zeile für Zeile.

## Für Agenten

14. **Gespeicherte Sichten** als benannte Filter (`overdue`, `casting_week`, `missing_docs`) — kürzere Prompts,
    weniger Fehler.
15. **Idempotenz-Schlüssel** für Schreibaufrufe, damit ein Retry keine doppelte Notiz erzeugt.
16. **Antwort-Budget:** Listen standardmäßig auf 25 Treffer begrenzen und Gesamtzahl mitliefern (ist bereits so).
