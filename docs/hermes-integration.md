# Hermes in die Ilvana-Integration einbinden

Hermes ist ein **Client** des Ilvana-MCP — er hält keine eigenen Daten, sondern ruft die 31 Werkzeuge auf.
Die Verbindung braucht drei Dinge: URL, CodeWords-Key, `X-Actor`.

## Verbindung

```json
{
  "mcpServers": {
    "ilvana-airtable": {
      "url": "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/mcp/",
      "headers": {
        "Authorization": "Bearer <CODEWORDS_API_KEY>",
        "X-Actor": "hermes"
      }
    }
  }
}
```

## Nachweis, dass Hermes angebunden ist

Der Dienst führt Buch über seine Clients. Zwei Aufrufe genügen:

```bash
# 1. Welche Clients kennt der Dienst, welche wurden tatsächlich gesehen?
curl -s -X POST "$ILVANA/tools/service_info" -H "Authorization: Bearer $KEY" \
     -H 'Content-Type: application/json' -d '{}' | jq '.result.clients'

# 2. Nur die Aktionen von Hermes
./scripts/ilvana.sh audit_list '{"limit":10,"actor":"hermes"}'
```

`clients.known` listet die vier vorgesehenen Clients (hermes, codex, chatgpt, grok),
`clients.seen` die tatsächlich aufgetretenen Aufrufer mit Anzahl und letztem Zeitpunkt.

**Stand:** Hermes ist noch nicht in `clients.seen` — solange die Konfiguration nicht in Hermes eingetragen
ist, arbeitet niemand unter diesem Namen. Das ist der ehrliche Indikator, ob die Integration wirklich steht.

## End-to-End prüfen

```bash
python3 scripts/test_mcp_e2e.py "Mihaljevic"
```

Spielt eine komplette Hermes-Sitzung durch: Handshake, Werkzeugliste, Suche, Aktenabruf, `service_info`.
Erwartet `MCP END-TO-END OK`.

## Rechte und Grenzen

- Hermes liest und schreibt nur über freigegebene Felder; Formeln und Anhänge sind gesperrt.
- Massenänderungen brauchen `confirm=true`, Strukturänderungen ebenfalls.
- Löschen ist nicht möglich — auch nicht für Hermes.
- Wissen: `skills/ilvana-airtable/SKILL.md` + `references/`, sonst kennt Hermes die Feldnamen nicht.
