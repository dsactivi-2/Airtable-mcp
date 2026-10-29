#!/usr/bin/env python3
"""Schreibt docs/airtable-schema.md neu aus dem Live-Schema des Ilvana-Dienstes.

Aufruf: CODEWORDS_API_KEY=... python3 scripts/sync_airtable_schema.py [kopieren|original]
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

BASE = os.environ.get("ILVANA_URL", "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7")
KEY = os.environ.get("CODEWORDS_API_KEY", "").strip()


def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def section(schema):
    lines = [f"## {schema['base_label']}", "", f"Base-ID: `{schema['base_id']}`", ""]
    for table in schema["tables"]:
        writable = sum(1 for f in table["fields"] if f["writable"])
        lines += [f"### {table['table']}", "",
                  f"Tabellen-ID: `{table['table_id']}` · {len(table['fields'])} Felder · "
                  f"{writable} schreibbar", "",
                  "| Feld | ID | Typ | schreibbar | Auswahl |", "|---|---|---|---|---|"]
        for field in table["fields"]:
            choices = ", ".join(field.get("choices") or []) or "—"
            lines.append(f"| {field['name'].replace('|', '/')} | `{field['id']}` | {field['type']} | "
                         f"{'ja' if field['writable'] else 'nein'} | {choices.replace('|', '/')} |")
        lines.append("")
    return lines


def main():
    if not KEY:
        sys.exit("CODEWORDS_API_KEY fehlt")
    bases = sys.argv[1:] or ["kopieren", "original"]
    lines = ["# Airtable-Schema — Ilvana i Hase", "",
             f"Generiert aus dem Live-Schema des Dienstes am {date.today().isoformat()}. "
             "Nicht von Hand bearbeiten.", ""]
    skipped = []
    for base in bases:
        try:
            lines += section(get(f"/schema?base={base}"))
        except urllib.error.HTTPError as exc:
            skipped.append(f"{base}: HTTP {exc.code}")
    if skipped:
        lines += ["## Nicht verfügbar", ""] + [f"- {item}" for item in skipped] + [""]
    os.makedirs("docs", exist_ok=True)
    with open("docs/airtable-schema.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"docs/airtable-schema.md geschrieben — {len(lines)} Zeilen"
          + (f", übersprungen: {skipped}" if skipped else ""))


if __name__ == "__main__":
    main()
