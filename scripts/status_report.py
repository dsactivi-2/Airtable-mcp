#!/usr/bin/env python3
"""Erzeugt status/status.json (Badge) und status/status.md (Übersicht).

Aufruf: CODEWORDS_API_KEY=... python3 scripts/status_report.py
Exit-Code 0 = alles grün, 1 = mindestens eine Auffälligkeit.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

MCP = os.environ.get("ILVANA_URL", "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7")
NOTION = os.environ.get("NOTION_URL", "https://runtime.codewords.ai/run/ilvana_notion_sync_0468633e")
RUNTIME = "https://runtime.codewords.ai/run"
KEY = os.environ.get("CODEWORDS_API_KEY", "").strip()


def call(url, method="GET", body=None, extra=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if extra:
        headers.update(extra)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def main():
    if not KEY:
        sys.exit("CODEWORDS_API_KEY fehlt")
    rows, problems = [], []

    health = call(f"{MCP}/health")
    version = health.get("version", "?")
    tools = health.get("tools", 0)
    rows.append(("Ilvana MCP", "erreichbar", f"{version}, {tools} Werkzeuge", tools >= 31))
    if tools < 31:
        problems.append(f"nur {tools} Werkzeuge")

    try:
        handshake = call(f"{MCP}/mcp/", "POST",
                         {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "status", "version": "1"}}},
                         {"Accept": "application/json, text/event-stream"})
        rows.append(("MCP", "Handshake", "ok", "serverInfo" in json.dumps(handshake)))
    except Exception as exc:  # noqa: BLE001
        rows.append(("MCP", "Handshake", str(exc)[:60], False))
        problems.append("MCP-Handshake fehlgeschlagen")

    try:
        status = call(f"{NOTION}/status")
        last = status.get("last_run", {})
        ok = bool(last.get("ok"))
        rows.append(("Notion-Sync", "letzter Lauf", f"{last.get('at', 'nie')} — {last.get('note', '')}"[:70], ok))
        if not ok:
            problems.append("Notion-Sync ohne erfolgreichen Lauf")
    except Exception as exc:  # noqa: BLE001
        rows.append(("Notion-Sync", "Status", str(exc)[:60], False))
        problems.append("Notion-Sync nicht erreichbar")

    try:
        schedules = call(f"{RUNTIME}/schedule_runs/list", "POST", {}).get("schedules") or []
        active = [s for s in schedules if s.get("active")]
        ours = [s for s in active if s.get("serviceName", "").startswith("Ilvana")]
        rows.append(("Zeitpläne", "aktiv", f"{len(ours)} (Ilvana)", len(ours) >= 4))
        if len(ours) < 4:
            problems.append(f"nur {len(ours)} aktive Ilvana-Zeitpläne")
    except Exception as exc:  # noqa: BLE001
        rows.append(("Zeitpläne", "Abfrage", str(exc)[:60], False))
        problems.append("Zeitpläne nicht abfragbar")

    healthy = not problems
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    os.makedirs("status", exist_ok=True)
    with open("status/status.json", "w", encoding="utf-8") as handle:
        json.dump({
            "schemaVersion": 1,
            "label": "Ilvana MCP",
            "message": f"{'ok' if healthy else 'stoerung'} · {tools} tools · v{version}",
            "color": "brightgreen" if healthy else "red",
        }, handle, ensure_ascii=False)
        handle.write("\n")

    lines = ["# Stack-Status", "", f"Stand: {stamp}", "",
             "| Komponente | Prüfung | Ergebnis | OK |", "|---|---|---|---|"]
    for component, check, result, ok in rows:
        lines.append(f"| {component} | {check} | {result} | {'✅' if ok else '❌'} |")
    lines += ["", f"**Gesamt: {'OK' if healthy else 'Auffällig'}**"]
    if problems:
        lines += ["", "Offene Punkte:"] + [f"- {p}" for p in problems]
    lines += ["", "_Automatisch erzeugt von `scripts/status_report.py` (GitHub Actions, stündlich)._"]
    with open("status/status.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    print("\n".join(f"{'OK  ' if ok else 'FEHL'} {c} / {ch}: {r}" for c, ch, r, ok in rows))
    print("Gesamt:", "OK" if healthy else f"{len(problems)} Auffälligkeit(en)")
    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
