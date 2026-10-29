# Auftrag an ChatGPT — Ilvana-Airtable-MCP als Action anbinden

ChatGPT spricht kein MCP. Der Weg ist ein eigener GPT mit einer Action über OpenAPI.

## 0. Ziel

Dein GPT beantwortet Kandidatenfragen aus Airtable, nicht aus dem Web.

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

**Aufrufer:** ChatGPT kann **keine** eigenen Header senden — `X-Actor` ist hier nicht möglich. Im Verlauf erscheint deshalb die Aufrufer-ID der Plattform, nicht `chatgpt`.

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

## Aufgabe A — Action anlegen

1. *Explore GPTs* → **Create** → Tab **Configure**
2. **Actions** → *Create new action* → **Import from URL**
   ```
   https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json
   ```
   Alternativ den Inhalt von `openapi/ilvana-airtable.openapi.json` einfügen.
3. **Authentication:** *API Key* → Auth Type **Bearer** → Wert = `CODEWORDS_API_KEY`
4. **Instructions:** Inhalt von `integrations/chatgpt/instructions.md` einfügen
5. **Knowledge:** `skills/ilvana-airtable/references/schema.md`, `filtering.md`, `tags.md` hochladen

## Grenzen, die du kennen und nennen musst

| Grenze | Folge |
|---|---|
| **30 Operationen pro Action** | Die Spec hat 34. Beim Import **vier weglassen**: `/`, `/automation/daily`, `/tools/schedule_sync`, `/tools/hook_test`. Bleiben exakt 30. |
| **Keine eigenen Header** | `X-Actor: chatgpt` ist nicht möglich — im Audit steht die Plattform-ID |
| **Keine Binärdaten** | `document_upload` braucht eine Datei-**Adresse** (`file`), keinen Chat-Upload |
| **Kein Streaming** | Antworten kommen als JSON, 6–12 Sekunden pro Aufruf |
| **Kein Key im Prompt** | Der Key steckt ausschließlich in der Action-Konfiguration |

## Aufgabe B — Selbsttest (Pflicht)

Stelle in einem neuen Chat diese Fragen und prüfe, ob **Werkzeuge** aufgerufen werden:

1. „Wer ist Haris Mihaljevic?" → `candidates_search`, dann `candidate_dossier`
2. „Was ist überfällig?" → `applications_search` mit `only_overdue`
3. „Wie ist der Stand in der Pipeline?" → `pipeline_summary`

Wenn der GPT stattdessen im Web sucht oder die Antwort erfindet: Action-Schema prüfen und die
Instructions verschärfen (Regel 1 ausdrücklich wiederholen).

## Aufgabe C — Abschlussbericht

```
Action importiert  : ja/nein · Operationen: <Anzahl>
Auth               : Bearer gesetzt
Knowledge          : <hochgeladene Dateien>
Selbsttest         : 3/3 · <Beobachtung>
Bekannte Grenzen   : kein X-Actor · keine Uploads · 30 Operationen
```

## Verbote

Keine Websuche nach Personennamen · kein Key im Prompt oder in Knowledge-Dateien ·
keine Massenänderung ohne `confirm` · keine Löschungen.
