#!/usr/bin/env python3
"""Erzeugt docs/api-reference.md und integrations/hermes/tools.json aus /schema/tools.

Aufruf:  CODEWORDS_API_KEY=... python3 scripts/generate_api_docs.py
"""
import json
import os
import sys
import urllib.request
from datetime import date

BASE = os.environ.get("ILVANA_URL", "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7")
KEY = os.environ.get("CODEWORDS_API_KEY", "").strip()
GROUPS = {
    "Lesen": ["schema_get", "candidates_search", "applications_search", "candidate_dossier",
              "application_get", "documents_list", "casting_ratings_list", "pipeline_summary", "due_report"],
    "Schreiben": ["application_create", "application_update", "applications_bulk_update", "application_add_note",
                  "casting_rating_upsert", "document_upload", "tasks_manage"],
    "Automatik": ["automation_rules", "automation_run", "automation_log"],
    "Betrieb": ["audit_list", "error_log", "alerts_list", "data_health", "hook_test", "config_get",
                "config_set", "service_info", "schedule_sync"],
    "Struktur": ["table_create", "field_create", "field_update"],
}


def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main():
    if not KEY:
        sys.exit("CODEWORDS_API_KEY fehlt")
    health = get("/health")
    tools = get("/schema/tools")["tools"]
    by_name = {t["function"]["name"]: t["function"] for t in tools}

    lines = ["# API-Referenz", "",
             f"Generiert aus `GET {BASE}/schema/tools` — Version {health['version']}, "
             f"{len(tools)} Werkzeuge, Stand {date.today().isoformat()}. Nicht von Hand bearbeiten.", "",
             "Alle Aufrufe: `POST /tools/<name>` mit JSON-Body, Auth per `Authorization: Bearer <CODEWORDS_API_KEY>`.", ""]
    for group, names in GROUPS.items():
        present = [n for n in names if n in by_name]
        lines += [f"## {group} ({len(present)})", ""]
        for name in present:
            fn = by_name[name]
            lines += [f"### `{name}`", "", fn.get("description", "").strip(), ""]
            props = (fn.get("parameters") or {}).get("properties") or {}
            required = set((fn.get("parameters") or {}).get("required") or [])
            if not props:
                lines += ["Keine Parameter.", ""]
                continue
            lines += ["| Parameter | Typ | Pflicht | Standard | Beschreibung |", "|---|---|---|---|---|"]
            for key, spec in props.items():
                kind = spec.get("type", "?")
                if isinstance(kind, list):
                    kind = "/".join(kind)
                desc = (spec.get("description") or "").replace("|", "/").strip()
                lines.append(f"| `{key}` | {kind} | {'ja' if key in required else 'nein'} | "
                             f"{spec.get('default', '—')} | {desc} |")
            lines.append("")
    os.makedirs("docs", exist_ok=True)
    with open("docs/api-reference.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    os.makedirs("integrations/hermes", exist_ok=True)
    with open("integrations/hermes/tools.json", "w", encoding="utf-8") as handle:
        json.dump({"version": health["version"], "source": f"{BASE}/schema/tools", "tools": tools},
                  handle, ensure_ascii=False, indent=1)

    unknown = sorted(set(by_name) - {n for names in GROUPS.values() for n in names})
    if unknown:
        print(f"Warnung: Werkzeuge ohne Gruppe: {unknown}")
    print(f"docs/api-reference.md geschrieben — {len(tools)} Werkzeuge, Version {health['version']}")


if __name__ == "__main__":
    main()
