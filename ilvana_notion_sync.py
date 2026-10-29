# /// script
# requires-python = "==3.11.*"
# dependencies = [
#   "codewords-client==0.4.11",
#   "fastapi==0.116.1",
#   "pydantic==2.11.7",
#   "httpx==0.28.1"
# ]
# [tool.env-checker]
# env_vars = [
#   "PORT=8000",
#   "LOGLEVEL=INFO",
#   "CODEWORDS_API_KEY",
#   "CODEWORDS_RUNTIME_URI",
#   "NOTION_TOKEN",
#   "NOTION_PARENT_PAGE"
# ]
# ///
"""
Notion-Sync für das Ilvana Airtable MCP.

Liest die Werkzeugschemata vom Live-Endpunkt `/schema/tools` und spiegelt sie in eine
Notion-Datenbank — eine Seite pro Werkzeug, mit Gruppe, Beschreibung, Parametern und Prüfsumme.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from codewords_client import logger, redis_client, run_service
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ILVANA_BASE = "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7"
NOTION_VERSION = "2022-06-28"
DB_TITLE = "Ilvana Tools"
STALE_HOURS = 26

GROUPS: dict[str, str] = {}
for _name in ("schema_get", "candidates_search", "applications_search", "candidate_dossier",
              "application_get", "documents_list", "casting_ratings_list", "pipeline_summary", "due_report"):
    GROUPS[_name] = "Lesen"
for _name in ("application_create", "application_update", "applications_bulk_update", "application_add_note",
              "casting_rating_upsert", "document_upload", "tasks_manage"):
    GROUPS[_name] = "Schreiben"
for _name in ("automation_rules", "automation_run", "automation_log"):
    GROUPS[_name] = "Automatik"
for _name in ("audit_list", "error_log", "alerts_list", "data_health", "hook_test", "config_get",
              "config_set", "service_info", "schedule_sync"):
    GROUPS[_name] = "Betrieb"
for _name in ("table_create", "field_create", "field_update"):
    GROUPS[_name] = "Struktur"


class NotionError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise NotionError(f"{name} ist nicht gesetzt.", status=500)
    return value


def _page_id(raw: str) -> str:
    """Accept a Notion URL or a UUID and return the 32-char id."""
    compact = re.sub(r"[^0-9a-fA-F]", "", raw)
    if len(compact) < 32:
        raise NotionError("NOTION_PARENT_PAGE enthält keine gültige Seiten-ID.", status=500)
    return compact[-32:]


def _chunks(text: str, size: int = 1900) -> list[dict[str, Any]]:
    text = text or ""
    parts = [text[i : i + size] for i in range(0, len(text), size)] or [""]
    return [{"type": "text", "text": {"content": part}} for part in parts[:100]]


def _rich(value: str) -> dict[str, Any]:
    return {"rich_text": _chunks(value)}


def _title(value: str) -> dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": value[:1900]}}]}


def _select(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


async def _notion(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _env("NOTION_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.request(method, f"https://api.notion.com/v1/{path}", headers=headers, json=payload)
    if response.status_code >= 400:
        try:
            detail = response.json().get("message") or response.text[:200]
        except Exception:  # noqa: BLE001
            detail = response.text[:200]
        if response.status_code == 404:
            raise NotionError(
                "Notion: Objekt nicht gefunden. Ist die Zielseite mit der Integration geteilt? "
                f"Details: {detail}", status=404,
            )
        raise NotionError(f"Notion-Fehler {response.status_code}: {detail}", status=502)
    return response.json()


async def _fetch_tools() -> tuple[list[dict[str, Any]], str]:
    key = _env("CODEWORDS_API_KEY")
    async with httpx.AsyncClient(timeout=60.0) as client:
        tools_resp = await client.get(f"{ILVANA_BASE}/schema/tools", headers={"Authorization": f"Bearer {key}"})
        health_resp = await client.get(f"{ILVANA_BASE}/health", headers={"Authorization": f"Bearer {key}"})
    if tools_resp.status_code != 200:
        raise NotionError(f"schema/tools antwortet mit {tools_resp.status_code}.", status=502)
    version = "unbekannt"
    if health_resp.status_code == 200:
        version = health_resp.json().get("version", "unbekannt")
    return tools_resp.json().get("tools", []), version


def _describe(tool: dict[str, Any]) -> tuple[str, str, str, str]:
    function = tool.get("function", {})
    name = function.get("name", "?")
    description = function.get("description", "")
    params = (function.get("parameters") or {}).get("properties") or {}
    required = set((function.get("parameters") or {}).get("required") or [])
    lines = []
    for key, spec in params.items():
        kind = spec.get("type", "?")
        if isinstance(kind, list):
            kind = "/".join(kind)
        flag = "Pflicht" if key in required else "optional"
        desc = (spec.get("description") or "").strip()
        default = spec.get("default", "-")
        lines.append(f"• {key} ({kind}, {flag}, Standard: {default}) — {desc}")
    params_text = "\n".join(lines) if lines else "keine Parameter"
    checksum = hashlib.sha256(
        json.dumps({"d": description, "p": params_text, "g": GROUPS.get(name, "Sonstige")}, ensure_ascii=False)
        .encode("utf-8")
    ).hexdigest()[:16]
    return description, params_text, ", ".join(sorted(required)) or "—", checksum


async def _find_database(parent: str) -> str | None:
    cursor = None
    while True:
        path = f"blocks/{parent}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
        data = await _notion("GET", path)
        for block in data.get("results", []):
            if block.get("type") == "child_database":
                title = "".join(part.get("plain_text", "") for part in block.get("child_database", {}).get("title", "") if isinstance(part, dict))
                if not title or title == DB_TITLE:
                    return block.get("id")
        if not data.get("has_more"):
            return None
        cursor = data.get("next_cursor")


async def _ensure_database(parent: str) -> tuple[str, bool]:
    existing = await _find_database(parent)
    if existing:
        return existing, False
    properties = {
        "Werkzeug": {"title": {}},
        "Gruppe": {"select": {"options": [{"name": g} for g in ("Lesen", "Schreiben", "Automatik", "Betrieb", "Struktur", "Sonstige")]}},
        "Beschreibung": {"rich_text": {}},
        "Parameter": {"rich_text": {}},
        "Pflichtfelder": {"rich_text": {}},
        "Prüfsumme": {"rich_text": {}},
        "Stand": {"date": {}},
    }
    created = await _notion("POST", "databases", {
        "parent": {"type": "page_id", "page_id": parent},
        "title": [{"type": "text", "text": {"content": DB_TITLE}}],
        "properties": properties,
    })
    return created.get("id"), True


async def _existing_pages(database_id: str) -> dict[str, dict[str, Any]]:
    pages: dict[str, dict[str, Any]] = {}
    cursor = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = await _notion("POST", f"databases/{database_id}/query", body)
        for page in data.get("results", []):
            props = page.get("properties", {})
            title = "".join(p.get("plain_text", "") for p in props.get("Werkzeug", {}).get("title", []))
            if title:
                pages[title] = page
        if not data.get("has_more"):
            return pages
        cursor = data.get("next_cursor")


def _properties(name: str, description: str, params: str, required: str, checksum: str) -> dict[str, Any]:
    return {
        "Werkzeug": _title(name),
        "Gruppe": _select(GROUPS.get(name, "Sonstige")),
        "Beschreibung": _rich(description),
        "Parameter": _rich(params),
        "Pflichtfelder": _rich(required),
        "Prüfsumme": _rich(checksum),
        "Stand": {"date": {"start": datetime.now(timezone.utc).isoformat(timespec="seconds")}},
    }


class SyncRequest(BaseModel):
    dry_run: bool = Field(default=False, description="true = nur Vorschau, Notion bleibt unverändert")


async def _store_heartbeat(payload: dict[str, Any]) -> None:
    try:
        async with redis_client() as (redis, ns):
            await redis.set(f"{ns}:last_run", json.dumps(payload, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Heartbeat nicht speicherbar", error=str(exc))


async def _read_heartbeat() -> dict[str, Any]:
    try:
        async with redis_client() as (redis, ns):
            raw = await redis.get(f"{ns}:last_run")
        return json.loads(raw) if raw else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Heartbeat nicht lesbar", error=str(exc))
        return {}


async def _alert(kind: str, message: str, details: dict[str, Any] | None = None) -> bool:
    url = (os.environ.get("ALERT_WEBHOOK_URL") or "").strip()
    entry = {
        "service": "ilvana-notion-sync",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "message": message,
        "details": details or {},
    }
    if not url:
        logger.info("Alarm ohne Webhook gespeichert", kind=kind)
        return False
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=entry)
        return 200 <= response.status_code < 300
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alarm nicht zustellbar", error=str(exc))
        return False


class CheckRequest(BaseModel):
    notify: bool = Field(default=True, description="false = nur prüfen, keinen Alarm senden")


class CheckResult(BaseModel):
    healthy: bool = Field(description="true = letzter Lauf erfolgreich und nicht zu alt")
    stale: bool = Field(description="true = letzter Lauf liegt länger als 26 Stunden zurück")
    last_run: str | None = Field(default=None, description="Zeitpunkt des letzten Laufs (UTC)")
    last_ok: bool = Field(default=False, description="Ergebnis des letzten Laufs")
    detail: str = Field(default="", description="Kurzbeschreibung des letzten Laufs")
    alerted: bool = Field(default=False, description="true = Alarm wurde ausgelöst")


class SyncResult(BaseModel):
    success: bool = Field(description="true bei erfolgreichem Lauf")
    dry_run: bool = Field(description="true = Vorschau, Notion wurde nicht verändert")
    version: str = Field(description="Version des Ilvana-Dienstes, aus /health")
    database_id: str | None = Field(default=None, description="ID der Notion-Datenbank")
    database_created: bool = Field(default=False, description="true, wenn die Datenbank in diesem Lauf entstanden ist")
    total: int = Field(default=0, description="Anzahl gefundener Werkzeuge")
    created: int = Field(default=0, description="neu angelegte Seiten")
    updated: int = Field(default=0, description="aktualisierte Seiten")
    unchanged: int = Field(default=0, description="unveränderte Seiten (Prüfsumme gleich)")
    tools: list[str] = Field(default_factory=list, description="Namen der synchronisierten Werkzeuge")
    note: str = Field(default="", description="Kurze Zusammenfassung des Laufs")


async def run_sync(dry_run: bool) -> SyncResult:
    logger.info("STEPLOG START fetchschema")
    tools, version = await _fetch_tools()
    if not tools:
        raise NotionError("Der Endpunkt liefert keine Werkzeuge.", status=502)
    parent = _page_id(_env("NOTION_PARENT_PAGE"))

    if dry_run:
        return SyncResult(
            success=True, dry_run=True, version=version, total=len(tools),
            tools=[t.get("function", {}).get("name", "?") for t in tools],
            note="Vorschau: Notion wurde nicht verändert.",
        )

    logger.info("STEPLOG START ensuredatabase")
    database_id, created_db = await _ensure_database(parent)
    existing = await _existing_pages(database_id)

    logger.info("STEPLOG START upsertpages")
    created = updated = unchanged = 0
    for tool in tools:
        name = tool.get("function", {}).get("name", "?")
        description, params, required, checksum = _describe(tool)
        props = _properties(name, description, params, required, checksum)
        page = existing.get(name)
        if page is None:
            await _notion("POST", "pages", {"parent": {"database_id": database_id}, "properties": props})
            created += 1
            continue
        current = "".join(
            part.get("plain_text", "")
            for part in page.get("properties", {}).get("Prüfsumme", {}).get("rich_text", [])
        )
        if current == checksum:
            unchanged += 1
            continue
        await _notion("PATCH", f"pages/{page['id']}", {"properties": props})
        updated += 1

    logger.info("Notion sync finished", created=created, updated=updated, unchanged=unchanged)
    await _store_heartbeat({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": True,
        "total": len(tools),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "version": version,
        "note": f"{created} neu, {updated} aktualisiert, {unchanged} unverändert.",
    })
    return SyncResult(
        success=True, dry_run=False, version=version, database_id=database_id, database_created=created_db,
        total=len(tools), created=created, updated=updated, unchanged=unchanged,
        tools=[t.get("function", {}).get("name", "?") for t in tools],
        note=f"{created} neu, {updated} aktualisiert, {unchanged} unverändert.",
    )


app = FastAPI(
    title="Ilvana Notion Sync",
    description="Spiegelt die Werkzeugschemata des Ilvana Airtable MCP in eine Notion-Datenbank.",
    version="1.0.0",
)


@app.exception_handler(NotionError)
async def notion_error_handler(request: Request, exc: NotionError) -> JSONResponse:
    logger.warning("Notion sync error", path=str(request.url), message=exc.message)
    await _store_heartbeat({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": False,
        "note": exc.message,
    })
    await _alert("notion_sync_failed", exc.message, {"path": str(request.url), "status": exc.status})
    return JSONResponse(status_code=exc.status, content={"success": False, "error": exc.message})


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "ilvana-notion-sync", "source": ILVANA_BASE, "database": DB_TITLE}


@app.get("/status")
async def status() -> dict[str, Any]:
    heartbeat = await _read_heartbeat()
    return {"service": "ilvana-notion-sync", "last_run": heartbeat, "stale_hours": STALE_HOURS}


@app.post("/check", response_model=CheckResult)
async def check(payload: CheckRequest) -> CheckResult:
    heartbeat = await _read_heartbeat()
    last_run = heartbeat.get("at")
    last_ok = bool(heartbeat.get("ok"))
    stale = True
    if last_run:
        try:
            stamp = datetime.fromisoformat(last_run)
            stale = (datetime.now(timezone.utc) - stamp).total_seconds() > STALE_HOURS * 3600
        except Exception:  # noqa: BLE001
            stale = True
    healthy = last_ok and not stale
    alerted = False
    if not healthy and payload.notify:
        if stale:
            message = f"Notion-Sync seit über {STALE_HOURS} Stunden nicht gelaufen (letzter Lauf: {last_run or 'nie'})"
            alerted = await _alert("notion_sync_stale", message, {"last_run": last_run})
        else:
            message = f"Notion-Sync fehlgeschlagen: {heartbeat.get('note', 'unbekannt')}"
            alerted = await _alert("notion_sync_failed", message, {"last_run": last_run})
    return CheckResult(healthy=healthy, stale=stale, last_run=last_run, last_ok=last_ok,
                       detail=str(heartbeat.get("note", "")), alerted=alerted)


@app.post("/preview", response_model=SyncResult)
async def preview(payload: SyncRequest) -> SyncResult:
    return await run_sync(dry_run=True)


@app.post("/", response_model=SyncResult)
async def sync(payload: SyncRequest) -> SyncResult:
    return await run_sync(dry_run=bool(payload.dry_run))


if __name__ == "__main__":
    run_service(app)
