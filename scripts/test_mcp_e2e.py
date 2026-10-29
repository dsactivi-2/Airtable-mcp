#!/usr/bin/env python3
"""End-to-End-Test der MCP-Anbindung, so wie Hermes sie nutzt.

Aufruf:  CODEWORDS_API_KEY=... python3 scripts/test_mcp_e2e.py [suchbegriff]
Exit-Code 0 = alle Schritte grün.
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("ILVANA_URL", "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7")
KEY = os.environ.get("CODEWORDS_API_KEY", "").strip()
URL = f"{BASE}/mcp/"
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
FAILED = []


def rpc(request_id, method, params=None):
    body = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(URL, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
    for line in raw.splitlines():
        if line.startswith("data:"):
            payload = json.loads(line[5:].strip())
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", "MCP-Fehler"))
            if payload.get("id") == request_id:
                return payload.get("result", {})
    raise RuntimeError("keine JSON-RPC-Antwort erhalten")


def step(name, condition, detail=""):
    print(f"  {'OK  ' if condition else 'FEHL'}  {name}{(' — ' + detail) if detail else ''}")
    if not condition:
        FAILED.append(name)


def main():
    if not KEY:
        sys.exit("CODEWORDS_API_KEY fehlt")
    query = sys.argv[1] if len(sys.argv) > 1 else "a"

    print("1) Handshake")
    init = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "e2e", "version": "1"}})
    step("initialize", "serverInfo" in init, init.get("serverInfo", {}).get("name", ""))

    print("2) Werkzeuge")
    tools = rpc(2, "tools/list").get("tools", [])
    step("tools/list", len(tools) >= 31, f"{len(tools)} Werkzeuge")

    print("3) Lesen")
    search = rpc(3, "tools/call", {"name": "candidates_search", "arguments": {"query": query, "limit": 3}})
    content = json.dumps(search, ensure_ascii=False)
    step("candidates_search", '"total"' in content, content[:80])
    hits = []
    try:
        for block in search.get("content", []):
            hits = json.loads(block.get("text", "{}")).get("result", {}).get("candidates", [])
    except Exception:
        pass
    step("Treffer vorhanden", bool(hits), f"{len(hits)} Kandidaten")

    print("4) Akte")
    if hits:
        dossier = rpc(4, "tools/call", {"name": "candidate_dossier",
                                        "arguments": {"record_id": hits[0]["record_id"]}})
        text = json.dumps(dossier, ensure_ascii=False)
        step("candidate_dossier", "pre_call_brief" in text, hits[0].get("name", ""))
    else:
        step("candidate_dossier", False, "übersprungen — kein Treffer")

    print("5) Betrieb")
    info = rpc(5, "tools/call", {"name": "service_info", "arguments": {}})
    text = json.dumps(info, ensure_ascii=False)
    step("service_info", "AIRTABLE_PAT" in text)
    step("Secrets gemeldet", '"configured": true' in text or '"configured":true' in text)

    print()
    if FAILED:
        print(f"FEHLGESCHLAGEN: {', '.join(FAILED)}")
        sys.exit(1)
    print("MCP END-TO-END OK")


if __name__ == "__main__":
    main()
