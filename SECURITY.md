# Sicherheit

## Zugangsdaten

| Geheimnis | Wo es liegt | Wer es bekommt |
|---|---|---|
| `AIRTABLE_PAT` | CodeWords-Dienst (verschlüsselt) | niemand sonst — kein Agent, kein Repo |
| `CODEWORDS_API_KEY` | beim Aufrufer (Agent/Plattform) | alle Agenten, als `Authorization: Bearer …` |
| `HOOK_SECRET` | Dienst-Konfiguration **und** Airtable-Automation | nur diese beiden Stellen |
| `ALERT_WEBHOOK_URL` | Dienst-Konfiguration | enthält oft ein Token in der URL — wie ein Passwort behandeln |

Im Repository stehen **keine** echten Werte. `.env.example` enthält nur Platzhalter, die CI prüft das.

## Schutzmechanismen im Dienst

- **Auth:** jeder Aufruf braucht einen gültigen Bearer-Key der Plattform.
- **Hook:** ohne gesetztes `HOOK_SECRET` ist `apply` **gesperrt** (HTTP 401); `preview` bleibt erlaubt.
  Mit Secret gilt: Header `X-Hook-Secret` muss exakt passen.
- **Schreib-Whitelist:** nur Felder, die Airtable als beschreibbar meldet. Formeln, Verknüpfungen und
  Anhänge werden abgelehnt — mit Liste der erlaubten Felder.
- **Auswahlwerte:** werden gegen die echten Optionen geprüft; keine stillen Neuanlagen.
- **Massenänderung:** Vorschau ist Standard, echte Ausführung nur mit `dry_run=false` **und**
  `confirm=true`, maximal 50 Datensätze.
- **Strukturänderungen:** Vorschau ist Standard, echte Ausführung nur mit `confirm=true`.
- **Kein Löschen:** weder Datensätze, Dateien, Tabellen noch Felder.
- **Uploads:** nur PDF, JPG, JPEG, PNG, DOC, DOCX bis 10 MB.
- **Protokoll:** jede Schreibaktion und jeder Fehler wird mit Aufrufer, Zeitpunkt und Ziel gespeichert.
- **Secrets in Antworten:** `config_get` und `alerts_list` geben nur `true/false` zurück, nie Werte.

## Aufrufer unterscheiden

Header `X-Actor: <name>` setzen. Ohne Header steht die Aufrufer-ID der Plattform im Protokoll.
So bleibt nachvollziehbar, welcher Agent was geändert hat.

## Schlüssel wechseln

1. CodeWords-Key neu erzeugen, in allen Agenten ersetzen.
2. Airtable-Token: neues Token anlegen, `AIRTABLE_PAT` im Panel ersetzen, altes Token löschen.
3. Hook-Secret: `config_set {"hook_secret": "<neu>"}` und denselben Wert in der Airtable-Automation.

## Datenschutz

Die Base enthält personenbezogene Daten (Name, Telefon, Passnummer, Dokumente). Deshalb:

- Agenten bekommen nur den CodeWords-Key, nie direkten Airtable-Zugang.
- In Beispielen, Schulungen und Videos nur anonimisierte Daten verwenden.
- Zugriff im Airtable-Token auf die benötigten Bases beschränken.

## Meldung von Problemen

Sicherheitsrelevante Beobachtung: Dienst sofort deaktivieren (Schedule pausieren, Key erneuern), dann
`audit_list` und `error_log` auswerten.
