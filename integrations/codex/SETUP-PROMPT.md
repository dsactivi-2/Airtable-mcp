# Auftrag an Codex — Ilvana-Airtable-MCP verdrahten

Gilt für Codex im Terminal, lokal oder auf einem VPS. Der Dienst läuft bereits.

## 0. Ziel

Codex soll für Kandidatenfragen ausschließlich das Ilvana-MCP nutzen. Das Repo
`dsactivi-2/Airtable-mcp` liefert Regeln (`AGENTS.md`), Skill (`skills/`) und Hilfsskripte mit.

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

**Aufrufer:** Header `X-Actor: codex` bei jedem Aufruf — Codex kann Header setzen.

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

## Aufgabe A — Verbindung herstellen

```bash
git clone https://github.com/dsactivi-2/Airtable-mcp.git
cd Airtable-mcp
export CODEWORDS_API_KEY="<DEIN_KEY>"
export ILVANA_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
export ILVANA_ACTOR="codex"
```

Zwei Wege, beide gültig:

**A1 — MCP** (bevorzugt, wenn deine Codex-Version MCP unterstützt). Trage in deiner
MCP-Konfiguration ein:

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": { "Authorization": "Bearer <DEIN_KEY>", "X-Actor": "codex" }
    }
  }
}
```

**A2 — REST** über den mitgelieferten Helfer:

```bash
./scripts/ilvana.sh candidates_search '{"query":"Mihaljevic"}'
```

Ermittle selbst, wo deine Konfiguration liegt, und **nenne den Pfad im Bericht**.

## Aufgabe B — Regeln prüfen

`AGENTS.md` im Repo-Wurzelverzeichnis enthält den Block `<!-- ilvana-mcp -->`.
Prüfe, ob er vorhanden ist. Fehlt er, ergänze ihn — sonst nichts ändern.

## Aufgabe C — Wissen laden

Lies vor der ersten Änderung:

- `skills/ilvana-airtable/SKILL.md` (Regeln, Werkzeuge, Grenzen)
- `skills/ilvana-airtable/references/schema.md` (Feldnamen, Auswahlwerte, schreibbar ja/nein)
- `skills/ilvana-airtable/references/filtering.md` (Suche und Filter)
- `skills/ilvana-airtable/references/writing.md` (Anlegen, Ändern, Uploads, Dubletten)

## Aufgabe D — Selbsttest (Pflicht)

```bash
python3 scripts/test_mcp_e2e.py "Mihaljevic"
./scripts/ilvana.sh audit_list '{"limit":5,"actor":"codex"}'
./scripts/ilvana.sh service_info '{}'
```

Erwartet: `MCP END-TO-END OK` (bzw. REST-Pfad mit 31 Werkzeugen), Audit zeigt deine Aufrufe unter
`codex`, `service_info` meldet Version und alle drei Secrets `true`.

## Aufgabe E — Abschlussbericht

```
Umgebung           : <lokal | VPS | Container>  · <Betriebssystem>
Konfigurationspfad : <gefunden oder "REST über scripts/ilvana.sh">
Transport          : MCP | REST   (Werkzeuge = 31)
AGENTS.md-Block    : vorhanden | ergänzt
Selbsttest         : <Ergebnis>
Offene Punkte      : <keine | was genau>
```

## Verhalten ab jetzt

| Frage | Weg |
|---|---|
| „Wer ist Haris Mihaljevic?" | `candidates_search` → `candidate_dossier` |
| „Was ist überfällig?" | `applications_search` mit `only_overdue` |
| „Wie ist der Stand?" | `pipeline_summary` |
| „Ändere bei allen …" | `applications_bulk_update` mit `dry_run: true`, dann bestätigen lassen |

## Verbote

Keine Websuche nach Personennamen · keine Secrets in Commits (`.gitignore` beachten) ·
keine Massenänderung ohne `confirm` · keine Löschungen.
