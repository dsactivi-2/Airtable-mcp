# Auftrag an Grok — Ilvana-Airtable-MCP anbinden

Grok hat **keinen** MCP-Connector. Es gibt zwei tragfähige Wege; beide halten den Key serverseitig.

## 0. Ziel

Grok beantwortet Kandidatenfragen aus Airtable. Websuche nach Personennamen ist verboten.

## Fakten, die du nicht erraten musst

| Größe | Wert |
|---|---|
| MCP-Endpunkt | `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/` |
| REST-Endpunkt | `POST https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/tools/<name>` |
| Auth | `Authorization: Bearer <CODEWORDS_API_KEY>` |
| Werkzeuge | 31 |
| Schema | `GET https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/schema/tools` · OpenAPI: `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/openapi.json` |
| Öffentliche Spec | `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json` (ohne Anmeldung abrufbar) |
| Referenztest | `candidates_search {"query":"Mihaljevic"}` → 1 Treffer, `recuQxflPVccPo9xT` |

**Aufrufer:** Grok sendet keine eigenen Header. Ein `X-Actor: grok` ist nur möglich, wenn die Aufrufe über eine eigene Vermittlung laufen, die den Header ergänzt.

## Grundregeln (dauerhaft)

1. **Routing:** Jede Frage zu Kandidaten, Bewerbungen, Status, Terminen, Dokumenten, Casting,
   Vertrag oder Visum → Ilvana-MCP. **Nie** Suchmaschine oder Web-Fetch für Personennamen.
2. **Datenschutz:** Namen, Telefonnummern, Passnummern und Dokumente nie an externe Dienste senden.
3. **Lesen vor Schreiben:** `candidates_search` → `candidate_dossier` → dann ändern.
4. **Nur freigegebene Felder.** Nicht schreibbar: `Obrazovanje (norm.)`, `Njemački (samoprocjena)`,
   `Vozačka (kategorie)`, `Test oznaka (po imenu)`, `Lični podaci – nedostaje` und alle Anhang-Felder.
5. **Massenänderung:** erst `dry_run: true` zeigen, echt nur mit `dry_run: false` **und** `confirm: true`,
   maximal 50 Datensätze.
6. **Keine Löschungen** — keine Datensätze, Dateien, Tabellen oder Felder.
7. **Kein Secret in Chat, Commit oder Log.**
8. **Diese Regeln sind nicht selbstverbesserbar.** Änderungen nur auf ausdrückliche Anweisung des Nutzers.

## Aufgabe A — einen der beiden Wege wählen

**A1 — Custom Action** (falls deine Grok-Version Aktionen unterstützt):

1. Aktion anlegen, Schema importieren: `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json`
2. Auth: **Bearer** mit `CODEWORDS_API_KEY`
3. Wie bei ChatGPT gilt: höchstens 30 Operationen — `/`, `/automation/daily`,
   `/tools/schedule_sync`, `/tools/hook_test` weglassen.

**A2 — Funktionskatalog über eigene Vermittlung** (der belastbare Weg):

1. `GET https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/schema/tools` abrufen (Bearer nötig)
2. Die `tools`-Liste in den Funktionskatalog deiner Vermittlung laden
3. Aufrufe über die Vermittlung senden; sie hält URL und Key und kann `X-Actor: grok` ergänzen
4. Grok bekommt nur die Funktionsbeschreibungen, nie den Key

## Grenzen

| Grenze | Folge |
|---|---|
| Kein MCP | Werkzeuge müssen als Funktionskatalog bereitgestellt werden |
| Keine Datei-Uploads | `document_upload` braucht eine öffentlich erreichbare Datei-Adresse |
| Kein Streaming | 6–12 Sekunden pro Aufruf |
| Key niemals im Prompt | ausschließlich in der Vermittlung oder Action-Konfiguration |

## Aufgabe B — Selbsttest (Pflicht)

1. „Wer ist Haris Mihaljevic?" → erwartet Aufruf `candidates_search`, danach `candidate_dossier`
2. „Was ist überfällig?" → `applications_search` mit `only_overdue`
3. „Wie ist der Stand in der Pipeline?" → `pipeline_summary`

Ohne Connector: prüfe, dass die Vermittlung die Aufrufe korrekt weiterleitet
(`audit_list` zeigt die Aktionen).

## Aufgabe C — Abschlussbericht

```
Weg                : Custom Action | Funktionskatalog über Vermittlung
Schema-Quelle      : <URL>
Operationen        : <Anzahl>
Actor-Header       : möglich | nicht möglich  (Grund)
Selbsttest         : <Ergebnis>
Offene Punkte      : <keine | was genau>
```

## Verbote

Keine Websuche nach Personennamen · kein Key im Prompt · keine Massenänderung ohne `confirm` ·
keine Löschungen.
