# Inbetriebnahme

Sieben Schritte, in dieser Reihenfolge. Alles andere ist schon deployed und geprüft.

- Dienst: `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7`
- MCP: `https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/`
- Öffentliche Spec: `https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json`
- Secrets: alle drei gesetzt (`AIRTABLE_PAT`, `HOOK_SECRET`, `ALERT_WEBHOOK_URL`)

---

## 1. Hermes Agent

Datei `integrations/hermes/mcp.json` übernehmen, `REPLACE_WITH_CODEWORDS_API_KEY` ersetzen:

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": {
        "Authorization": "Bearer REPLACE_WITH_CODEWORDS_API_KEY",
        "X-Actor": "hermes"
      }
    }
  }
}
```

`X-Actor: hermes` sorgt dafür, dass im Verlauf (`audit_list`) steht, wer gehandelt hat.
Danach `skills/ilvana-airtable/SKILL.md` als Projektwissen laden.

**Prüfen:** Hermes fragt „Wer ist Haris Mihaljevic?" → sollte `candidates_search` aufrufen.

---

## 2. Codex

```bash
git clone https://github.com/dsactivi-2/Airtable-mcp.git
cd Airtable-mcp
export CODEWORDS_API_KEY="<key>"
export ILVANA_URL="https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
export ILVANA_ACTOR="codex"
```

- `AGENTS.md` liest Codex automatisch (Regeln, Werkzeugliste, Verweise).
- MCP-Variante: `integrations/codex/mcp.json` übernehmen.
- REST-Variante: `./scripts/ilvana.sh candidates_search '{"query":"Mihaljevic"}'`

---

## 3. ChatGPT und Grok

Beide importieren die Spec **per URL**, keine Datei nötig:

```
https://cdn.jsdelivr.net/gh/dsactivi-2/Airtable-mcp@main/openapi/ilvana-airtable.openapi.json
```

1. Action/Integration anlegen → *Import from URL* → obige URL
2. Authentication: **API Key**, Typ **Bearer**, Wert = CodeWords-Key
3. Instructions: Inhalt von `integrations/chatgpt/instructions.md`

Details: `integrations/chatgpt/action.md`, `integrations/grok/action.md`.
ChatGPT erlaubt 30 Operationen pro Action — der Dienst hat genau 30.

---

## 4. Airtable-Automation

1. Base **Ilvana i Hase (Kopieren)** → *Automations* → *Create automation*
2. Trigger: *When record matches conditions* (z. B. Status = `Casting`) oder *When record updated*
3. Aktion **Run a script**, Input-Variable `recordId` = *Record ID* des Triggers
4. Code aus `integrations/airtable/automation-script.js` einfügen, Platzhalter ersetzen
5. Starten mit `MODE = "preview"` → Ergebnis im Skript-Log prüfen
6. Erst wenn das passt: `MODE = "apply"` und Automation aktivieren

Das Secret gehört **in den JSON-Body** — Header `X-Hook-Secret` entfernt das Gateway.
Schritt für Schritt: `integrations/airtable/README.md`.

---

## 5. Original-Base freigeben

Im Airtable-Token (`AIRTABLE_PAT`) unter **Access** die Base *Ilvana i Hase* ergänzen.
Prüfen:

```bash
./scripts/ilvana.sh pipeline_summary '{"base":"original"}'
```

- `200` → freigegeben
- `403` → noch nicht im Token, Meldung nennt den Grund

Heute ist nur *Kopieren* freigegeben; Schreibzugriff auf *Original* ist bewusst nicht aktiv.

---

## 6. Testdaten aufräumen

In Airtable von Hand löschen (der Dienst darf nicht löschen):

| Was | Wo |
|---|---|
| `[TEST] Anlage API` (`recrTzk9nJE0P5lRL`) | Prijave (test) |
| Bewertung `reczQ4vAgKzNpTsAa` | Casting ocjene |
| Aufgabe `recdET7uPZphcv1Fn` | Table 1 |
| Anhang `[TEST] systemtest.pdf` | Datensatz `recPceen76ZUQ29MI`, Feld *Sonstige Dokumente* |
| Notizen mit `[TEST] …`, Felder *Sljedeća akcija* / *Rok akcije* | Datensatz `recPceen76ZUQ29MI` |

---

## 7. Tageslauf scharf stellen

Aktiv: **apply**, täglich **07:00 Ortszeit** (`cron(0 6 * * ? *)` = 06:00 UTC, gilt für Europe/Berlin und Sarajevo).

Ein **zweiter** Zeitplan (`cron(0 3 * * ? *)`) ruft täglich `schedule_sync` auf und stellt den Tagesplan
auf den Sommer-/Winterwert um: Sommerzeit → `cron(0 5 * * ? *)`, Winterzeit → `cron(0 6 * * ? *)`.
Damit bleibt es ganzjährig bei 07:00 Ortszeit, ohne manuellen Eingriff.

Ein Cron kennt keine Zeitumstellung: in der Sommerzeit läuft der Job dadurch um **08:00** Ortszeit.

Der Modus steckt im JSON-Body, nicht in der URL (Query-Parameter kommen über die Runtime nicht an):

Der Lauf prüft alle Bewerbungen, erzeugt den Tagesbericht und zeigt geplante Folgeaufgaben — ohne zu
schreiben. Wenn die Regeln fachlich passen:

```bash
curl -X POST "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/automation/daily" \
  -H "Authorization: Bearer $CODEWORDS_API_KEY"
```

Alternativ nur die Regeln testen, ohne den Tageslauf umzustellen:

```bash
./scripts/ilvana.sh automation_run '{"mode":"apply","record_ids":["rec…"]}'
```

Jeder Datensatz wird pro Regel genau einmal verändert (Marker, 180 Tage), alles landet in `audit_list`.

---

## 8. Abschlussprüfung

```bash
export CODEWORDS_API_KEY="<key>"
export HOOK_SECRET="<hook-secret>"
./scripts/check-installation.sh
```

Prüft: Version, 30 Werkzeuge, alle drei Secrets, Hook-Sperre ohne Secret und Freigabe mit Secret,
Lesetest auf *Kopieren*, Status der Original-Base. Gibt am Ende `BEREIT` oder eine Liste offener Punkte.
