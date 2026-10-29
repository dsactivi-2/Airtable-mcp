# /// script
# requires-python = "==3.11.*"
# dependencies = [
#   "codewords-client==0.4.11",
#   "fastapi==0.116.1",
#   "pydantic==2.11.7",
#   "fastmcp==2.10.6",
#   "httpx==0.28.1"
# ]
# [tool.env-checker]
# env_vars = [
#   "PORT=8000",
#   "LOGLEVEL=INFO",
#   "CODEWORDS_API_KEY",
#   "CODEWORDS_RUNTIME_URI",
#   "AIRTABLE_PAT",
#   "ALERT_WEBHOOK_URL=",
#   "HOOK_SECRET="
# ]
# ///
"""
Ilvana i Hase — Airtable MCP server + REST API.

Exposes both Airtable bases ("Ilvana i Hase (Kopieren)" and "Ilvana i Hase")
to AI assistants as MCP tools and as plain JSON HTTP endpoints, and runs the
recurring automation (daily due report, follow-up tasks on status change).
"""

import base64
import json
import os
import re
import time
import unicodedata
from contextvars import ContextVar
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

import httpx
from codewords_client import logger, redis_client, run_service
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.exceptions import McpError
from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------- constants
BASES: dict[str, str] = {
    "kopieren": "appz3VFomHaWhuILV",
    "original": "appV4ApSY55wEaXf4",
}
BASE_LABEL = {
    "kopieren": "Ilvana i Hase (Kopieren)",
    "original": "Ilvana i Hase",
}
TABLE_NAMES = {"prijave": "Prijave (test)", "casting": "Casting ocjene", "tasks": "Table 1"}

ATTACH_FIELDS = ["Lebenslauf", "Reisepass", "Führerschein", "Zeugnisse", "Foto", "Sonstige Dokumente"]
EXT_TO_TYPE = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

NON_WRITABLE_TYPES = {
    "formula", "rollup", "count", "aiText", "multipleRecordLinks", "multipleAttachments",
    "singleCollaborator", "createdTime", "lastModifiedTime", "autoNumber", "button",
    "barcode", "externalSyncSource",
}
FINAL_STATUSES = {"Počeo sa radom", "ODBIJEN", "Odustao"}
REQUIRED_DOCS = ["DIPLOMA", "SLIKA PASOŠA", "FOTOGRAFIJA ZA CV"]
EARLY_STATUSES = {"Zainteresiran", "Zeleni / obrada"}

TZ = ZoneInfo("Europe/Sarajevo")
SCHEMA_TTL = 300
_schema_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_ACTOR: ContextVar[str] = ContextVar("actor", default="api")

WRITE_TOOLS = {
    "application_create",
    "application_update",
    "applications_bulk_update",
    "application_add_note",
    "casting_rating_upsert",
    "document_upload",
    "tasks_manage",
    "automation_rules",
    "automation_run",
}

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "id": "status_casting",
        "kind": "status",
        "status": "Casting",
        "task": "Einladung + Termin bestätigen",
        "next_action": "Termin bestätigen und Kandidat einladen",
        "due_days": 2,
    },
    {
        "id": "status_primljeni",
        "kind": "status",
        "status": "Primljeni",
        "task": "Unterlagen prüfen",
        "next_action": "Fehlende Dokumente prüfen und anfordern",
        "due_days": 3,
    },
    {
        "id": "status_ugovor",
        "kind": "status",
        "status": "Ugovor",
        "task": "Vertrag versenden",
        "next_action": "Vertrag versenden",
        "due_days": 3,
    },
    {
        "id": "status_viziranje",
        "kind": "status",
        "status": "Viziranje",
        "task": "Visumsunterlagen prüfen",
        "next_action": "Visumsunterlagen prüfen und Termin bestätigen",
        "due_days": 5,
    },
    {
        "id": "appointment_2d",
        "kind": "appointment",
        "field": "Termin casting",
        "days_before": 2,
        "task": "Kandidat erinnern",
        "next_action": "Kandidat an den Termin erinnern",
        "due_days": 0,
    },
]

# ---------------------------------------------------------------- utilities
class AirtableError(Exception):
    """Domain error with a user facing message and an HTTP status."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


async def _append_log(key: str, entry: dict[str, Any], cap: int = 1000) -> None:
    """Write one entry to a capped Redis list (audit, errors, alerts)."""
    try:
        async with redis_client() as (redis, ns):
            await redis.lpush(f"{ns}:{key}", json.dumps(entry, ensure_ascii=False))
            await redis.ltrim(f"{ns}:{key}", 0, cap - 1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Log write failed", key=key, error=str(exc))


async def _config() -> dict[str, Any]:
    """Runtime configuration stored in Redis (overrides environment variables)."""
    try:
        async with redis_client() as (redis, ns):
            raw = await redis.get(f"{ns}:config")
        if raw:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Config read failed", error=str(exc))
    return {}


async def _config_save(values: dict[str, Any]) -> dict[str, Any]:
    current = await _config()
    current.update(values)
    current = {k: v for k, v in current.items() if v is not None}
    async with redis_client() as (redis, ns):
        await redis.set(f"{ns}:config", json.dumps(current, ensure_ascii=False))
    return current


async def _effective(key: str, env_name: str | None = None) -> str:
    config = await _config()
    return str(config.get(key) or os.environ.get(env_name or key.upper(), "") or "").strip()


async def _push_alert(kind: str, message: str, details: dict[str, Any] | None = None) -> bool:
    """Store an alert and push it to the configured alert webhook."""
    entry = {
        "at": _now_iso(),
        "kind": kind,
        "message": message,
        "details": details or {},
        "actor": _ACTOR.get(),
    }
    await _append_log("alerts", entry, 500)
    url = await _effective("alert_webhook_url")
    if not url:
        logger.info("Alert stored (no webhook configured)", kind=kind)
        return False
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(url, json={"service": "ilvana-airtable", **entry})
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alert webhook failed", error=str(exc))
        return False


def _record_ids_of(result: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("record_id", "rating_id", "task_id"):
        value = result.get(key)
        if value:
            ids.append(str(value))
    for item in (result.get("record_ids") or [])[:50]:
        ids.append(str(item))
    return ids[:50]


def _norm_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.lower()).strip()


def _norm_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def _phone_match(left: Any, right: Any) -> bool:
    a, b = _norm_phone(left), _norm_phone(right)
    if not a or not b:
        return False
    size = min(len(a), len(b), 9)
    if size < 6:
        return a == b
    return a[-size:] == b[-size:]


def _today() -> date:
    return datetime.now(TZ).date()


def _now_iso() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.000Z", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[: len(fmt) + 4], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _status_of(fields: dict[str, Any]) -> str:
    return str(fields.get("Status kandidata") or "").strip()


def _candidate_name(fields: dict[str, Any]) -> str:
    return str(fields.get("Ime i prezime") or "").strip()


def _candidate_phone(fields: dict[str, Any]) -> str:
    prefix = str(fields.get("Pozivni broj") or "").strip()
    number = str(fields.get("Broj telefona") or "").strip()
    return f"{prefix} {number}".strip()


def _documents(fields: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for field in ATTACH_FIELDS:
        for item in fields.get(field) or []:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "field": field,
                    "filename": item.get("filename"),
                    "type": item.get("type"),
                    "size": item.get("size"),
                    "url": item.get("url"),
                }
            )
    return result


def _missing_documents(fields: dict[str, Any]) -> list[str]:
    status = _status_of(fields)
    if status in EARLY_STATUSES or status == "":
        return []
    present = {str(x).strip().upper() for x in (fields.get("Dokumenti") or [])}
    return [doc for doc in REQUIRED_DOCS if doc.upper() not in present]


def _base_id(base: str) -> str:
    key = (base or "kopieren").strip().lower()
    if key not in BASES:
        raise AirtableError(f"Unbekannte Base '{base}'. Erlaubt: {', '.join(BASES)}")
    return BASES[key]


def _pat() -> str:
    token = (os.environ.get("AIRTABLE_PAT") or "").strip()
    if not token:
        raise AirtableError("AIRTABLE_PAT ist nicht gesetzt.", status=500)
    return token


async def _at_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {_pat()}"}
    headers.update(kwargs.pop("headers", {}))
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.request(method, url, headers=headers, **kwargs)
    if response.status_code >= 400:
        try:
            payload = response.json()
            detail = payload.get("error", payload)
        except Exception:  # noqa: BLE001
            detail = response.text[:300]
        if response.status_code == 403:
            raise AirtableError(
                "Kein Zugriff auf diese Airtable-Base. Der Zugangsschlüssel muss die Base "
                "unter \"Access\" enthalten. Details: " + str(detail)[:200],
                status=403,
            )
        if response.status_code == 404:
            raise AirtableError(f"Airtable: nicht gefunden. Details: {str(detail)[:200]}", status=404)
        if response.status_code == 422:
            raise AirtableError(f"Airtable lehnt die Felder ab: {str(detail)[:300]}", status=422)
        raise AirtableError(f"Airtable-Fehler {response.status_code}: {str(detail)[:300]}", status=502)
    return response.json()


async def _base_schema(base: str, refresh: bool = False) -> list[dict[str, Any]]:
    base_id = _base_id(base)
    cached = _schema_cache.get(base_id)
    if cached and not refresh and time.time() - cached[0] < SCHEMA_TTL:
        return cached[1]
    payload = await _at_request("GET", f"https://api.airtable.com/v0/meta/bases/{base_id}/tables")
    tables = payload.get("tables", [])
    _schema_cache[base_id] = (time.time(), tables)
    return tables


async def _table_id(base: str, table_key: str) -> str:
    if table_key not in TABLE_NAMES:
        raise AirtableError(f"Unbekannte Tabelle '{table_key}'. Erlaubt: {', '.join(TABLE_NAMES)}")
    wanted = TABLE_NAMES[table_key]
    for table in await _base_schema(base):
        if table.get("name") == wanted:
            return table["id"]
    logger.error("Table not found in schema", base=base, table=wanted)
    raise AirtableError(
        f"Tabelle '{wanted}' wurde in der Base '{BASE_LABEL[base]}' nicht gefunden. "
        "Bitte Tabellennamen in Airtable prüfen.",
        status=404,
    )


async def _table_fields(base: str, table_key: str) -> dict[str, dict[str, Any]]:
    wanted = TABLE_NAMES.get(table_key)
    for table in await _base_schema(base):
        if table.get("name") == wanted:
            return {field["name"]: field for field in table.get("fields", [])}
    raise AirtableError(f"Tabelle '{wanted}' wurde in der Base nicht gefunden.", status=404)


def _is_writable(field: dict[str, Any]) -> bool:
    return field.get("type") not in NON_WRITABLE_TYPES


def _validate_fields(fields_by_name: dict[str, dict[str, Any]], fields: dict[str, Any], table_label: str) -> dict[str, Any]:
    if not fields:
        raise AirtableError("Es wurden keine Felder übergeben.")
    cleaned: dict[str, Any] = {}
    writable = sorted(name for name, meta in fields_by_name.items() if _is_writable(meta))
    unknown = [name for name in fields if name not in fields_by_name or not _is_writable(fields_by_name[name])]
    if unknown:
        raise AirtableError(
            f"Nicht schreibbare Felder in {table_label}: {', '.join(unknown)}. "
            f"Erlaubt: {', '.join(writable)}"
        )
    for name, value in fields.items():
        meta = fields_by_name[name]
        field_type = meta.get("type")
        if field_type in {"singleSelect", "multipleSelects"} and value not in (None, "", []):
            choices = [choice["name"] for choice in (meta.get("options") or {}).get("choices", [])]
            values = value if field_type == "multipleSelects" else [value]
            invalid = [item for item in values if item not in choices]
            if invalid:
                raise AirtableError(
                    f"Ungültiger Wert für '{name}': {', '.join(map(str, invalid))}. "
                    f"Erlaubt: {', '.join(choices) or '(keine Auswahl)'}"
                )
        if field_type == "rating" and value not in (None, ""):
            maximum = (meta.get("options") or {}).get("max", 5)
            if not isinstance(value, int) or not 0 <= value <= maximum:
                raise AirtableError(f"'{name}' erwartet eine Zahl zwischen 0 und {maximum}.")
        if field_type == "date" and isinstance(value, str) and value and _parse_date(value) is None:
            raise AirtableError(f"'{name}' erwartet ein Datum im Format YYYY-MM-DD.")
        cleaned[name] = value
    return cleaned


async def _fetch_records(
    base: str,
    table_key: str,
    max_records: int = 2000,
) -> list[dict[str, Any]]:
    base_id = _base_id(base)
    table_id = await _table_id(base, table_key)
    records: list[dict[str, Any]] = []
    offset: str | None = None
    while True:
        params: dict[str, Any] = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        payload = await _at_request(
            "GET", f"https://api.airtable.com/v0/{base_id}/{table_id}", params=params
        )
        records.extend(payload.get("records", []))
        offset = payload.get("offset")
        if not offset or len(records) >= max_records:
            break
    return records[:max_records]


async def _create_records(base: str, table_key: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_id = _base_id(base)
    table_id = await _table_id(base, table_key)
    created: list[dict[str, Any]] = []
    for start in range(0, len(rows), 10):
        chunk = [{"fields": row} for row in rows[start : start + 10]]
        payload = await _at_request(
            "POST", f"https://api.airtable.com/v0/{base_id}/{table_id}", json={"records": chunk}
        )
        created.extend(payload.get("records", []))
    return created


async def _patch_records(base: str, table_key: str, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_id = _base_id(base)
    table_id = await _table_id(base, table_key)
    patched: list[dict[str, Any]] = []
    for start in range(0, len(updates), 10):
        payload = await _at_request(
            "PATCH",
            f"https://api.airtable.com/v0/{base_id}/{table_id}",
            json={"records": updates[start : start + 10]},
        )
        patched.extend(payload.get("records", []))
    return patched


async def _get_record(base: str, table_key: str, record_id: str) -> dict[str, Any]:
    base_id = _base_id(base)
    table_id = await _table_id(base, table_key)
    return await _at_request(
        "GET", f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
    )


def _brief(fields: dict[str, Any]) -> dict[str, Any]:
    rok = _parse_date(fields.get("Rok akcije"))
    return {
        "record_id": fields.get("_record_id"),
        "name": _candidate_name(fields),
        "phone": _candidate_phone(fields),
        "status": _status_of(fields),
        "casting_group": fields.get("Casting grupa"),
        "casting_outcome": fields.get("Casting ishod"),
        "casting_date": fields.get("Termin casting"),
        "visa_date": fields.get("Termin vize"),
        "start_date": fields.get("Datum početka rada"),
        "next_action": fields.get("Sljedeća akcija"),
        "action_due": fields.get("Rok akcije"),
        "overdue": bool(rok and rok < _today() and _status_of(fields) not in FINAL_STATUSES),
        "missing_documents": _missing_documents(fields),
        "customer_number": fields.get("Kundennummer"),
        "passport": fields.get("Br. pasoša"),
    }


async def _records_brief(base: str, max_records: int = 3000) -> list[dict[str, Any]]:
    records = await _fetch_records(base, "prijave", max_records=max_records)
    briefs = []
    for record in records:
        fields = dict(record.get("fields") or {})
        fields["_record_id"] = record["id"]
        briefs.append(_brief(fields))
    return briefs


# ---------------------------------------------------------------- input models
BaseName = Literal["kopieren", "original"]


class SchemaGetInput(BaseModel):
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    include_choices: bool = Field(default=True, description="Auswahlwerte mitliefern")
    refresh: bool = Field(default=False, description="Schema neu von Airtable laden")


class CandidatesSearchInput(BaseModel):
    query: str | None = Field(default=None, description="Freitext: Name, Kundennummer, Passnummer")
    phone: str | None = Field(default=None, description="Handy- oder Festnetznummer, beliebiges Format")
    status: str | None = Field(default=None, description="Status kandidata (exakt)")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    limit: int = Field(default=25, ge=1, le=100, description="Treffer pro Seite")
    offset: int = Field(default=0, ge=0, description="Seiten-Offset")


class ApplicationsSearchInput(BaseModel):
    query: str | None = Field(default=None, description="Freitext über Name, Telefon, Kundennummer, Passnummer")
    phone: str | None = Field(default=None, description="Telefonnummer in beliebigem Format")
    status_kandidata: str | None = Field(default=None, description="Status kandidata exakt, z.B. Casting, Primljeni, Ugovor")
    casting_grupa: str | None = Field(default=None, description="Casting-Gruppe: UJUTRO oder POPODNE")
    casting_ishod: str | None = Field(default=None, description="Casting-Ergebnis, z.B. Došao, Prošao praktični")
    ugovor_tok: str | None = Field(default=None, description="Vertragsstand: Priprema, Poslato kandidatu, Potpisan, Poslato nadležnima")
    visa_ishod: str | None = Field(default=None, description="Visum-Ergebnis: Dopuna, Dobio vizu, Odbijenica")
    casting_from: str | None = Field(default=None, description="Termin casting ab (YYYY-MM-DD)")
    casting_to: str | None = Field(default=None, description="Termin casting bis (YYYY-MM-DD)")
    action_due_before: str | None = Field(default=None, description="Rok akcije vor (YYYY-MM-DD)")
    only_overdue: bool = Field(default=False, description="Nur überfällige Aktionen")
    only_missing_documents: bool = Field(default=False, description="Nur unvollständige Unterlagen")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    sort_by: str = Field(default="action_due", description="action_due | name | status | casting_date")
    sort_dir: Literal["asc", "desc"] = Field(default="asc", description="Sortierrichtung")
    limit: int = Field(default=25, ge=1, le=100, description="Treffer pro Seite")
    offset: int = Field(default=0, ge=0, description="Seiten-Offset")


class CandidateDossierInput(BaseModel):
    record_id: str | None = Field(default=None, description="Airtable-Datensatz-ID (rec…)")
    query: str | None = Field(default=None, description="Alternativ: Name")
    phone: str | None = Field(default=None, description="Alternativ: Telefonnummer")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class ApplicationGetInput(BaseModel):
    record_id: str = Field(..., description="Airtable-Datensatz-ID (rec…)")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class DocumentsListInput(BaseModel):
    record_id: str = Field(..., description="Airtable-Datensatz-ID (rec…)")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class CastingRatingsListInput(BaseModel):
    candidate_record_id: str | None = Field(default=None, description="Nur Bewertungen dieses Kandidaten")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    limit: int = Field(default=50, ge=1, le=100, description="Maximale Anzahl")


class PipelineSummaryInput(BaseModel):
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class DueReportInput(BaseModel):
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    days_ahead: int = Field(default=7, ge=1, le=60, description="Termine der nächsten X Tage")


class ApplicationUpdateInput(BaseModel):
    record_id: str = Field(..., description="Airtable-Datensatz-ID (rec…)")
    fields: dict[str, Any] = Field(..., description="Zu setzende Felder (nur freigegebene)")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    note: str | None = Field(default=None, description="Optionaler Protokoll-Eintrag")


class ApplicationCreateInput(BaseModel):
    fields: dict[str, Any] = Field(..., description="Felder des neuen Datensatzes; 'Ime i prezime' ist Pflicht")
    note: str | None = Field(default=None, description="Optionaler Startvermerk in 'Bilješka'")
    allow_duplicate: bool = Field(default=False, description="true = trotz gleicher Telefonnummer anlegen")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class BulkUpdateInput(BaseModel):
    fields: dict[str, Any] = Field(..., description="Zu setzende Felder für alle Treffer")
    record_ids: list[str] | None = Field(default=None, description="Explizite Datensatz-IDs")
    filter: dict[str, Any] | None = Field(default=None, description="Filter wie bei applications_search")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    limit: int = Field(default=50, ge=1, le=50, description="Maximal 50 Datensätze pro Aufruf")
    dry_run: bool = Field(default=True, description="true = nur Vorschau")
    confirm: bool = Field(default=False, description="Muss true sein, damit geschrieben wird")


class AddNoteInput(BaseModel):
    record_id: str = Field(..., description="Airtable-Datensatz-ID (rec…)")
    note: str = Field(..., min_length=1, max_length=4000, description="Notiztext")
    author: str = Field(default="agent", max_length=80, description="Verfasser, erscheint in der Notiz")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class CastingRatingInput(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict, description="Bewertungsfelder")
    rating_id: str | None = Field(default=None, description="Vorhandene Bewertung aktualisieren")
    candidate_record_id: str | None = Field(default=None, description="Kandidat verknüpfen")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class DocumentUploadInput(BaseModel):
    record_id: str = Field(..., description="Airtable-Datensatz-ID (rec…)")
    field: str = Field(..., description="Anhang-Feld, z.B. Lebenslauf")
    file: str = Field(
        ...,
        min_length=3,
        description="Datei (pdf, jpg, jpeg, png, doc, docx) — Adresse des Datei-Uploaders",
        json_schema_extra={"contentMediaType": "application/octet-stream"},
    )
    filename: str | None = Field(default=None, description="Dateiname mit Endung; sonst aus der Datei abgeleitet")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    note: str | None = Field(default=None, description="Optionaler Eintrag in 'Bemerkung zu Dokumenten'")


class TasksManageInput(BaseModel):
    action: Literal["list", "create", "update"] = Field(default="list", description="list, create oder update")
    task_id: str | None = Field(default=None, description="rec… für update")
    name: str | None = Field(default=None, description="Aufgabentitel")
    notes: str | None = Field(default=None, description="Beschreibung der Aufgabe")
    status: Literal["Todo", "In progress", "Done"] | None = Field(default=None, description="Aufgabenstatus")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    limit: int = Field(default=25, ge=1, le=100, description="Treffer pro Seite")


class AutomationRulesInput(BaseModel):
    action: Literal["get", "set"] = Field(default="get", description="get = Regeln ansehen, set = Regeln überschreiben")
    rules: list[dict[str, Any]] | None = Field(default=None, description="Regeln (nur bei action=set)")


class AutomationRunInput(BaseModel):
    mode: Literal["preview", "apply"] = Field(default="preview", description="preview = nur zeigen, apply = schreiben")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    limit: int = Field(default=300, ge=1, le=1000, description="Maximale Anzahl Datensätze")
    record_ids: list[str] | None = Field(
        default=None, description="Optional nur diese Datensätze prüfen (z.B. für einen Testlauf)"
    )


class AutomationLogInput(BaseModel):
    limit: int = Field(default=25, ge=1, le=200, description="Anzahl Einträge")


class RootRequest(BaseModel):
    tool: str | None = Field(default=None, description="Optional: Werkzeugname für Direktaufruf")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Argumente für das Werkzeug")


class ToolResponse(BaseModel):
    success: bool = Field(default=True, description="Immer true bei Erfolg")
    tool: str = Field(..., description="Name des ausgeführten Werkzeugs")
    result: dict[str, Any] = Field(default_factory=dict, description="Ergebnis des Werkzeugs als JSON")


class RootResponse(BaseModel):
    success: bool = Field(default=True, description="Immer true")
    service: str = Field(default="Ilvana Airtable MCP", description="Dienstname")
    tools: list[str] = Field(default_factory=list, description="Verfügbare Werkzeuge")
    usage: str = Field(default="", description="Kurzanleitung")
    result: dict[str, Any] | None = Field(default=None, description="Ergebnis bei Direktaufruf")


# ---------------------------------------------------------------- tool logic
async def tool_schema_get(m: SchemaGetInput) -> dict[str, Any]:
    logger.info("STEPLOG START schema_get")
    tables = await _base_schema(m.base, refresh=m.refresh)
    out = []
    for table in tables:
        fields = []
        for field in table.get("fields", []):
            entry: dict[str, Any] = {
                "name": field["name"],
                "id": field["id"],
                "type": field["type"],
                "writable": _is_writable(field),
            }
            if m.include_choices and field.get("type") in {"singleSelect", "multipleSelects"}:
                entry["choices"] = [c["name"] for c in (field.get("options") or {}).get("choices", [])]
            fields.append(entry)
        out.append(
            {
                "table": table["name"],
                "table_id": table["id"],
                "primary_field": table.get("primaryFieldId"),
                "fields": fields,
            }
        )
    return {"base": m.base, "base_id": BASES[m.base], "base_label": BASE_LABEL[m.base], "tables": out}


def _matches_text(fields: dict[str, Any], query: str) -> bool:
    needle = _norm_text(query)
    if not needle:
        return True
    haystack = " ".join(
        _norm_text(fields.get(key))
        for key in (
            "Ime i prezime", "Ime", "Prezime", "Kundennummer", "Br. pasoša",
            "Broj telefona", "Pozivni broj", "Bilješka", "Sljedeća akcija",
        )
    )
    return needle in haystack


def _matches_phone(fields: dict[str, Any], phone: str) -> bool:
    full = f"{fields.get('Pozivni broj') or ''}{fields.get('Broj telefona') or ''}"
    return _phone_match(phone, fields.get("Broj telefona")) or _phone_match(phone, full)


async def _filtered_records(m: ApplicationsSearchInput) -> list[dict[str, Any]]:
    records = await _fetch_records(m.base, "prijave", max_records=3000)
    casting_from = _parse_date(m.casting_from)
    casting_to = _parse_date(m.casting_to)
    due_before = _parse_date(m.action_due_before)
    selected: list[dict[str, Any]] = []
    for record in records:
        fields = record.get("fields") or {}
        if m.status_kandidata and _status_of(fields) != m.status_kandidata.strip():
            continue
        if m.casting_grupa and str(fields.get("Casting grupa") or "") != m.casting_grupa:
            continue
        if m.casting_ishod and str(fields.get("Casting ishod") or "") != m.casting_ishod:
            continue
        if m.ugovor_tok and str(fields.get("Ugovor tok") or "") != m.ugovor_tok:
            continue
        if m.visa_ishod and str(fields.get("Viza ishod") or "") != m.visa_ishod:
            continue
        casting_date = _parse_date(fields.get("Termin casting"))
        if casting_from and (not casting_date or casting_date < casting_from):
            continue
        if casting_to and (not casting_date or casting_date > casting_to):
            continue
        if due_before:
            due = _parse_date(fields.get("Rok akcije"))
            if not due or due > due_before:
                continue
        if m.query and not _matches_text(fields, m.query):
            continue
        if m.phone and not _matches_phone(fields, m.phone):
            continue
        enriched = dict(fields)
        enriched["_record_id"] = record["id"]
        brief = _brief(enriched)
        if m.only_overdue and not brief["overdue"]:
            continue
        if m.only_missing_documents and not brief["missing_documents"]:
            continue
        selected.append(brief)
    reverse = m.sort_dir == "desc"
    if m.sort_by in {"name", "status", "casting_date", "action_due"}:
        selected.sort(key=lambda item: (_norm_text(item.get(m.sort_by) or "")), reverse=reverse)
    return selected


async def tool_candidates_search(m: CandidatesSearchInput) -> dict[str, Any]:
    logger.info("STEPLOG START candidates_search")
    records = await _fetch_records(m.base, "prijave", max_records=3000)
    hits = []
    for record in records:
        fields = dict(record.get("fields") or {})
        fields["_record_id"] = record["id"]
        if m.query and not _matches_text(fields, m.query):
            continue
        if m.phone and not _matches_phone(fields, m.phone):
            continue
        if m.status and _status_of(fields) != m.status.strip():
            continue
        hits.append(_brief(fields))
    total = len(hits)
    page = hits[m.offset : m.offset + m.limit]
    return {
        "base": m.base,
        "total": total,
        "returned": len(page),
        "offset": m.offset,
        "candidates": page,
    }


async def tool_applications_search(m: ApplicationsSearchInput) -> dict[str, Any]:
    logger.info("STEPLOG START applications_search")
    hits = await _filtered_records(m)
    total = len(hits)
    page = hits[m.offset : m.offset + m.limit]
    return {
        "base": m.base,
        "base_label": BASE_LABEL[m.base],
        "total": total,
        "returned": len(page),
        "offset": m.offset,
        "applications": page,
    }


async def _resolve_candidate(m: CandidateDossierInput) -> dict[str, Any]:
    if m.record_id:
        record = await _get_record(m.base, "prijave", m.record_id)
        return record
    records = await _fetch_records(m.base, "prijave", max_records=3000)
    for record in records:
        fields = record.get("fields") or {}
        if m.phone and _matches_phone(fields, m.phone):
            return record
        if m.query and _matches_text(fields, m.query):
            return record
    raise AirtableError("Kein Kandidat gefunden. Bitte record_id, Name oder Telefonnummer prüfen.", status=404)


async def tool_candidate_dossier(m: CandidateDossierInput) -> dict[str, Any]:
    logger.info("STEPLOG START candidate_dossier")
    record = await _resolve_candidate(m)
    fields = record.get("fields") or {}
    record_id = record["id"]
    brief = _brief({**fields, "_record_id": record_id})
    ratings_all = await _fetch_records(m.base, "casting", max_records=1000)
    ratings = []
    for rating in ratings_all:
        linked = (rating.get("fields") or {}).get("Kandidat") or []
        if record_id not in linked:
            continue
        rfields = dict(rating.get("fields") or {})
        rfields.pop("Kandidat", None)
        ratings.append({"rating_id": rating["id"], **rfields})
    tasks_all = await _fetch_records(m.base, "tasks", max_records=1000)
    name_key = _norm_text(_candidate_name(fields))
    tasks = [
        {
            "task_id": task["id"],
            "name": (task.get("fields") or {}).get("Name"),
            "status": (task.get("fields") or {}).get("Status"),
            "notes": (task.get("fields") or {}).get("Notes"),
        }
        for task in tasks_all
        if name_key and name_key in _norm_text((task.get("fields") or {}).get("Name"))
    ]
    return {
        "base": m.base,
        "base_label": BASE_LABEL[m.base],
        "record_id": record_id,
        "summary": brief,
        "identity": {
            "name": _candidate_name(fields),
            "first_name": fields.get("Ime"),
            "last_name": fields.get("Prezime"),
            "phone": _candidate_phone(fields),
            "customer_number": fields.get("Kundennummer"),
            "passport": fields.get("Br. pasoša"),
            "birth_date": fields.get("Datum rođenja"),
            "applied_at": fields.get("Datum i vrijeme prijave"),
        },
        "process": {
            "status": _status_of(fields),
            "casting_group": fields.get("Casting grupa"),
            "casting_outcome": fields.get("Casting ishod"),
            "contract_state": fields.get("Ugovor tok"),
            "visa_outcome": fields.get("Viza ishod"),
            "documents_selected": fields.get("Dokumenti") or [],
            "activities": fields.get("Aktivnosti") or [],
            "next_action": fields.get("Sljedeća akcija"),
            "action_due": fields.get("Rok akcije"),
        },
        "dates": {
            "casting": fields.get("Termin casting"),
            "visa": fields.get("Termin vize"),
            "start_work": fields.get("Datum početka rada"),
        },
        "documents": _documents(fields),
        "missing_documents": brief["missing_documents"],
        "casting_ratings": ratings,
        "tasks": tasks,
        "notes": fields.get("Bilješka"),
        "document_note": fields.get("Bemerkung zu Dokumenten"),
        "pre_call_brief": _pre_call_brief(fields, brief, ratings),
    }


def _pre_call_brief(fields: dict[str, Any], brief: dict[str, Any], ratings: list[dict[str, Any]]) -> str:
    parts = [f"{brief['name'] or 'Kandidat'} — Status: {brief['status'] or 'unbekannt'}."]
    if brief["phone"]:
        parts.append(f"Telefon {brief['phone']}.")
    if fields.get("Termin casting"):
        parts.append(f"Casting-Termin {fields['Termin casting']} ({fields.get('Casting grupa') or 'ohne Gruppe'}).")
    if fields.get("Termin vize"):
        parts.append(f"Visum-Termin {fields['Termin vize']}.")
    if brief["next_action"]:
        due = brief["action_due"] or "ohne Frist"
        parts.append(f"Nächste Aktion: {brief['next_action']} ({due}).")
    if brief["missing_documents"]:
        parts.append("Fehlende Unterlagen: " + ", ".join(brief["missing_documents"]) + ".")
    if ratings:
        scores = [r.get("Stručnost (1-5)") for r in ratings if isinstance(r.get("Stručnost (1-5)"), int)]
        if scores:
            parts.append(f"Bewertung (Stručnost): {round(sum(scores) / len(scores), 1)} von 5.")
    return " ".join(parts)


async def tool_application_get(m: ApplicationGetInput) -> dict[str, Any]:
    logger.info("STEPLOG START application_get")
    record = await _get_record(m.base, "prijave", m.record_id)
    fields = record.get("fields") or {}
    return {
        "base": m.base,
        "record_id": record["id"],
        "created_time": record.get("createdTime"),
        "fields": fields,
        "summary": _brief({**fields, "_record_id": record["id"]}),
        "documents": _documents(fields),
    }


async def tool_documents_list(m: DocumentsListInput) -> dict[str, Any]:
    logger.info("STEPLOG START documents_list")
    record = await _get_record(m.base, "prijave", m.record_id)
    fields = record.get("fields") or {}
    documents = _documents(fields)
    return {
        "base": m.base,
        "record_id": record["id"],
        "name": _candidate_name(fields),
        "count": len(documents),
        "documents": documents,
        "note": fields.get("Bemerkung zu Dokumenten"),
    }


async def tool_casting_ratings_list(m: CastingRatingsListInput) -> dict[str, Any]:
    logger.info("STEPLOG START casting_ratings_list")
    ratings_all = await _fetch_records(m.base, "casting", max_records=1000)
    out = []
    for rating in ratings_all:
        fields = dict(rating.get("fields") or {})
        linked = fields.pop("Kandidat", None) or []
        if m.candidate_record_id and m.candidate_record_id not in linked:
            continue
        out.append({"rating_id": rating["id"], "candidate_ids": linked, **fields})
        if len(out) >= m.limit:
            break
    return {"base": m.base, "count": len(out), "ratings": out}


async def tool_pipeline_summary(m: PipelineSummaryInput) -> dict[str, Any]:
    logger.info("STEPLOG START pipeline_summary")
    briefs = await _records_brief(m.base)
    counts: dict[str, int] = {}
    for item in briefs:
        counts[item["status"] or "(leer)"] = counts.get(item["status"] or "(leer)", 0) + 1
    today = _today()
    upcoming = [item for item in briefs if _parse_date(item["casting_date"]) and today <= _parse_date(item["casting_date"]) <= today + timedelta(days=7)]
    return {
        "base": m.base,
        "total": len(briefs),
        "by_status": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "overdue_actions": sum(1 for item in briefs if item["overdue"]),
        "missing_documents": sum(1 for item in briefs if item["missing_documents"]),
        "appointments_next_7_days": len(upcoming),
        "without_next_action": sum(1 for item in briefs if not item["next_action"] and item["status"] not in FINAL_STATUSES),
    }


async def tool_due_report(m: DueReportInput) -> dict[str, Any]:
    logger.info("STEPLOG START due_report")
    briefs = await _records_brief(m.base)
    today = _today()
    horizon = today + timedelta(days=m.days_ahead)
    overdue = [item for item in briefs if item["overdue"]]
    appointments = []
    for item in briefs:
        casting = _parse_date(item["casting_date"])
        visa = _parse_date(item["visa_date"])
        for kind, value in (("casting", casting), ("visa", visa)):
            if value and today <= value <= horizon:
                appointments.append({**item, "appointment_type": kind, "appointment_date": value.isoformat()})
    appointments.sort(key=lambda item: item["appointment_date"])
    missing = [item for item in briefs if item["missing_documents"]]
    lines = [f"Tagesbericht {BASE_LABEL[m.base]} — {today.isoformat()}", ""]
    lines.append(f"Überfällige Aktionen: {len(overdue)}")
    for item in overdue[:20]:
        lines.append(f"  - {item['name']} ({item['status']}), fällig {item['action_due']}: {item['next_action'] or 'ohne Eintrag'}")
    lines.append(f"Termine in den nächsten {m.days_ahead} Tagen: {len(appointments)}")
    for item in appointments[:20]:
        label = "Casting" if item["appointment_type"] == "casting" else "Visum"
        lines.append(f"  - {item['appointment_date']} {label}: {item['name']} ({item['casting_group'] or 'ohne Gruppe'})")
    lines.append(f"Unvollständige Unterlagen: {len(missing)}")
    for item in missing[:20]:
        lines.append(f"  - {item['name']}: {', '.join(item['missing_documents'])}")
    return {
        "base": m.base,
        "date": today.isoformat(),
        "overdue_actions": overdue,
        "upcoming_appointments": appointments,
        "missing_documents": missing,
        "report_text": "\n".join(lines),
    }


async def tool_application_create(m: ApplicationCreateInput) -> dict[str, Any]:
    logger.info("STEPLOG START application_create")
    fields_by_name = await _table_fields(m.base, "prijave")
    cleaned = _validate_fields(fields_by_name, m.fields, "Prijave (test)")
    name = str(cleaned.get("Ime i prezime") or "").strip()
    if not name:
        raise AirtableError("'Ime i prezime' ist Pflicht — ohne Namen wird nichts angelegt.")
    phone = f"{cleaned.get('Pozivni broj') or ''}{cleaned.get('Broj telefona') or ''}"
    if phone.strip() and not m.allow_duplicate:
        for record in await _fetch_records(m.base, "prijave", max_records=3000):
            existing = record.get("fields") or {}
            existing_phone = f"{existing.get('Pozivni broj') or ''}{existing.get('Broj telefona') or ''}"
            if _phone_match(phone, existing_phone):
                raise AirtableError(
                    "Es gibt bereits einen Datensatz mit dieser Nummer: "
                    f"{_candidate_name(existing) or record['id']} ({record['id']}). "
                    "Mit allow_duplicate=true trotzdem anlegen oder den bestehenden Datensatz ändern.",
                    status=409,
                )
    if m.note:
        cleaned["Bilješka"] = f"[{_now_iso()} {_ACTOR.get()}] {m.note}"
    created = await _create_records(m.base, "prijave", [cleaned])
    record = created[0] if created else {"id": None, "fields": {}}
    logger.info("Application created", base=m.base, record_id=record.get("id"))
    return {
        "success": True,
        "base": m.base,
        "record_id": record.get("id"),
        "created_fields": cleaned,
        "summary": _brief({**(record.get("fields") or {}), "_record_id": record.get("id")}),
    }


async def tool_application_update(m: ApplicationUpdateInput) -> dict[str, Any]:
    logger.info("STEPLOG START application_update")
    fields_by_name = await _table_fields(m.base, "prijave")
    cleaned = _validate_fields(fields_by_name, m.fields, "Prijave (test)")
    if m.note:
        existing = (await _get_record(m.base, "prijave", m.record_id)).get("fields", {}) or {}
        previous = str(existing.get("Bilješka") or "").strip()
        cleaned["Bilješka"] = (previous + "\n" if previous else "") + f"[{_now_iso()} agent] {m.note}"
    patched = await _patch_records(m.base, "prijave", [{"id": m.record_id, "fields": cleaned}])
    logger.info("Application updated", base=m.base, record_id=m.record_id, fields=list(cleaned))
    return {
        "success": True,
        "base": m.base,
        "record_id": m.record_id,
        "updated_fields": cleaned,
        "record": patched[0] if patched else None,
    }


async def tool_bulk_update(m: BulkUpdateInput) -> dict[str, Any]:
    logger.info("STEPLOG START applications_bulk_update")
    fields_by_name = await _table_fields(m.base, "prijave")
    cleaned = _validate_fields(fields_by_name, m.fields, "Prijave (test)")
    target_ids: list[str] = []
    if m.record_ids:
        target_ids = list(dict.fromkeys(m.record_ids))[: m.limit]
    elif m.filter:
        search = ApplicationsSearchInput(base=m.base, limit=m.limit, **m.filter)
        hits = await _filtered_records(search)
        target_ids = [item["record_id"] for item in hits[: m.limit]]
    else:
        raise AirtableError("Bitte record_ids oder filter angeben — ohne Ziel keine Änderung.")
    if not target_ids:
        return {"success": True, "matched": 0, "dry_run": m.dry_run, "records": []}
    if m.dry_run or not m.confirm:
        return {
            "success": True,
            "dry_run": True,
            "matched": len(target_ids),
            "fields": cleaned,
            "note": "Vorschau — nichts geschrieben. Zum Ausführen dry_run=false und confirm=true setzen.",
            "record_ids": target_ids,
        }
    patched = await _patch_records(
        m.base, "prijave", [{"id": rid, "fields": cleaned} for rid in target_ids]
    )
    async with redis_client() as (redis, ns):
        await redis.lpush(
            f"{ns}:log",
            json.dumps(
                {
                    "at": _now_iso(),
                    "action": "bulk_update",
                    "base": m.base,
                    "count": len(target_ids),
                    "fields": list(cleaned),
                },
                ensure_ascii=False,
            ),
        )
        await redis.ltrim(f"{ns}:log", 0, 499)
    logger.info("Bulk update applied", base=m.base, count=len(patched))
    return {"success": True, "dry_run": False, "matched": len(target_ids), "updated": len(patched), "fields": cleaned}


async def tool_add_note(m: AddNoteInput) -> dict[str, Any]:
    logger.info("STEPLOG START application_add_note")
    record = await _get_record(m.base, "prijave", m.record_id)
    previous = str((record.get("fields") or {}).get("Bilješka") or "").strip()
    entry = f"[{_now_iso()} {m.author}] {m.note.strip()}"
    updated = (previous + "\n" if previous else "") + entry
    fields_by_name = await _table_fields(m.base, "prijave")
    _validate_fields(fields_by_name, {"Bilješka": updated}, "Prijave (test)")
    await _patch_records(m.base, "prijave", [{"id": m.record_id, "fields": {"Bilješka": updated}}])
    return {"success": True, "record_id": m.record_id, "appended": entry}


async def tool_casting_rating_upsert(m: CastingRatingInput) -> dict[str, Any]:
    logger.info("STEPLOG START casting_rating_upsert")
    fields_by_name = await _table_fields(m.base, "casting")
    writable = {name: meta for name, meta in fields_by_name.items() if _is_writable(meta)}
    payload = {k: v for k, v in (m.fields or {}).items() if k != "Kandidat"}
    cleaned = _validate_fields(writable, payload, "Casting ocjene") if payload else {}
    if m.candidate_record_id:
        cleaned["Kandidat"] = [m.candidate_record_id]
    if m.rating_id:
        patched = await _patch_records(m.base, "casting", [{"id": m.rating_id, "fields": cleaned}])
        return {"success": True, "rating_id": m.rating_id, "record": patched[0] if patched else None}
    if not cleaned:
        raise AirtableError("Keine Felder für die neue Bewertung übergeben.")
    if not cleaned.get("Oznaka") and m.candidate_record_id:
        candidate = await _get_record(m.base, "prijave", m.candidate_record_id)
        name = _candidate_name(candidate.get("fields") or {}) or m.candidate_record_id
        cleaned["Oznaka"] = f"{name} — {cleaned.get('Termin casting') or _today().isoformat()}"
    created = await _create_records(m.base, "casting", [cleaned])
    return {"success": True, "rating_id": created[0]["id"] if created else None, "record": created[0] if created else None}


async def tool_document_upload(m: DocumentUploadInput) -> dict[str, Any]:
    logger.info("STEPLOG START document_upload")
    field_name = m.field.strip()
    allowed_fields = ATTACH_FIELDS + ["Attachments"]
    if field_name not in allowed_fields:
        raise AirtableError(f"Unbekanntes Anhang-Feld '{field_name}'. Erlaubt: {', '.join(allowed_fields)}")
    spec = (m.file or "").strip()
    name = (m.filename or spec.rsplit("/", 1)[-1].split("?")[0] or "datei").strip()
    if spec.startswith("data:"):
        mime = spec[5:].split(";")[0].strip().lower()
        if "." not in name:
            suffix = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png",
                      "application/msword": "doc",
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}.get(mime, "")
            if suffix:
                name = f"{name or 'datei'}.{suffix}"
    extension = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
    if extension not in EXT_TO_TYPE:
        raise AirtableError(
            f"Dateityp '{extension or 'ohne Endung'}' ist nicht erlaubt. Erlaubt: pdf, jpg, jpeg, png, doc, docx"
        )
    body: dict[str, Any] = {"filename": name}
    if spec.startswith("data:"):
        raw = spec.partition(",")[2]
        try:
            data = base64.b64decode(raw, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise AirtableError(f"Dateiinhalt ist kein gültiges Base64: {exc}") from exc
        if len(data) > MAX_UPLOAD_BYTES:
            raise AirtableError(f"Datei ist größer als 10 MB ({len(data)} Bytes).")
        body["file"] = base64.b64encode(data).decode()
        body["contentType"] = EXT_TO_TYPE[extension]
    elif spec.startswith("http"):
        body["url"] = spec
    else:
        raise AirtableError("Bitte die vom Datei-Uploader bereitgestellte Adresse übergeben.")

    table_key = "tasks" if field_name == "Attachments" else "prijave"
    before = await _get_record(m.base, table_key, m.record_id)
    previous = list((before.get("fields") or {}).get(field_name) or [])
    base_id = _base_id(m.base)
    url = f"https://content.airtable.com/v0/{base_id}/{m.record_id}/{field_name}/uploadAttachment"
    await _at_request("POST", url, json=body)
    after = await _get_record(m.base, table_key, m.record_id)
    uploaded = list((after.get("fields") or {}).get(field_name) or [])
    if len(uploaded) <= len(previous):
        keep = [{"id": item["id"]} for item in previous if item.get("id")]
        merged = keep + [{"id": item["id"]} for item in uploaded if item.get("id")]
        await _patch_records(m.base, table_key, [{"id": m.record_id, "fields": {field_name: merged}}])
        uploaded = list(((await _get_record(m.base, table_key, m.record_id)).get("fields") or {}).get(field_name) or [])
    if m.note and table_key == "prijave":
        await tool_add_note(
            AddNoteInput(record_id=m.record_id, note=f"Datei '{name}' in {field_name}: {m.note}", base=m.base)
        )
    logger.info("Document uploaded", base=m.base, record_id=m.record_id, field=field_name)
    return {
        "success": True,
        "record_id": m.record_id,
        "field": field_name,
        "filename": name,
        "attachments": [
            {"id": item.get("id"), "filename": item.get("filename"), "size": item.get("size"), "type": item.get("type"), "url": item.get("url")}
            for item in uploaded
        ],
    }


async def tool_tasks_manage(m: TasksManageInput) -> dict[str, Any]:
    logger.info("STEPLOG START tasks_manage")
    if m.action == "list":
        records = await _fetch_records(m.base, "tasks", max_records=m.limit)
        return {
            "base": m.base,
            "count": len(records),
            "tasks": [
                {
                    "task_id": record["id"],
                    "name": (record.get("fields") or {}).get("Name"),
                    "status": (record.get("fields") or {}).get("Status"),
                    "notes": (record.get("fields") or {}).get("Notes"),
                }
                for record in records
            ],
        }
    fields_by_name = await _table_fields(m.base, "tasks")
    fields = {k: v for k, v in {"Name": m.name, "Notes": m.notes, "Status": m.status}.items() if v is not None}
    cleaned = _validate_fields(fields_by_name, fields, "Table 1")
    if m.action == "create":
        created = await _create_records(m.base, "tasks", [cleaned])
        return {"success": True, "task_id": created[0]["id"] if created else None, "record": created[0] if created else None}
    if not m.task_id:
        raise AirtableError("Für action=update wird task_id benötigt.")
    patched = await _patch_records(m.base, "tasks", [{"id": m.task_id, "fields": cleaned}])
    return {"success": True, "task_id": m.task_id, "record": patched[0] if patched else None}


async def _rules() -> list[dict[str, Any]]:
    async with redis_client() as (redis, ns):
        stored = await redis.get(f"{ns}:rules")
    if not stored:
        return DEFAULT_RULES
    try:
        rules = json.loads(stored)
        return rules if isinstance(rules, list) and rules else DEFAULT_RULES
    except Exception:  # noqa: BLE001
        return DEFAULT_RULES


async def tool_automation_rules(m: AutomationRulesInput) -> dict[str, Any]:
    logger.info("STEPLOG START automation_rules")
    if m.action == "set":
        if not m.rules:
            raise AirtableError("Für action=set werden rules benötigt.")
        for rule in m.rules:
            if "id" not in rule or "kind" not in rule:
                raise AirtableError("Jede Regel braucht mindestens 'id' und 'kind' (status|appointment).")
            if rule["kind"] == "status" and not rule.get("status"):
                raise AirtableError(f"Regel {rule['id']}: 'status' fehlt.")
            if rule["kind"] == "appointment" and not rule.get("field"):
                raise AirtableError(f"Regel {rule['id']}: 'field' fehlt.")
        async with redis_client() as (redis, ns):
            await redis.set(f"{ns}:rules", json.dumps(m.rules, ensure_ascii=False))
        return {"success": True, "rules": m.rules}
    rules = await _rules()
    return {"rules": rules, "source": "custom" if rules is not DEFAULT_RULES else "default"}


async def tool_automation_run(m: AutomationRunInput) -> dict[str, Any]:
    logger.info("STEPLOG START automation_run")
    rules = await _rules()
    records = await _fetch_records(m.base, "prijave", max_records=m.limit)
    if m.record_ids:
        wanted = set(m.record_ids)
        records = [record for record in records if record["id"] in wanted]
    today = _today()
    planned: list[dict[str, Any]] = []
    async with redis_client() as (redis, ns):
        for record in records:
            fields = record.get("fields") or {}
            status = _status_of(fields)
            name = _candidate_name(fields) or record["id"]
            for rule in rules:
                if rule.get("kind") == "status":
                    if status != str(rule.get("status", "")).strip():
                        continue
                elif rule.get("kind") == "appointment":
                    target = _parse_date(fields.get(rule.get("field", "Termin casting")))
                    if not target:
                        continue
                    if not (0 <= (target - today).days <= int(rule.get("days_before", 2))):
                        continue
                else:
                    continue
                marker = f"{ns}:auto:{rule['id']}:{record['id']}"
                if await redis.exists(marker):
                    continue
                action_due = (today + timedelta(days=int(rule.get("due_days", 0) or 0))).isoformat()
                planned.append(
                    {
                        "rule": rule["id"],
                        "record_id": record["id"],
                        "name": name,
                        "status": status,
                        "task": rule.get("task"),
                        "next_action": rule.get("next_action"),
                        "action_due": action_due,
                    }
                )
                if m.mode == "apply":
                    update_fields: dict[str, Any] = {}
                    if rule.get("next_action"):
                        update_fields["Sljedeća akcija"] = rule["next_action"]
                    update_fields["Rok akcije"] = action_due
                    previous = str(fields.get("Bilješka") or "").strip()
                    update_fields["Bilješka"] = (previous + "\n" if previous else "") + (
                        f"[{_now_iso()} automatisch] {rule.get('next_action') or rule['id']} (Frist {action_due})"
                    )
                    await _patch_records(m.base, "prijave", [{"id": record["id"], "fields": update_fields}])
                    if rule.get("task"):
                        await _create_records(
                            m.base,
                            "tasks",
                            [
                                {
                                    "Name": f"{name} — {rule['task']}",
                                    "Notes": f"Ausgelöst durch Regel {rule['id']} (Status {status or 'unbekannt'}), Frist {action_due}",
                                    "Status": "Todo",
                                }
                            ],
                        )
                    await redis.set(marker, "1", ex=60 * 60 * 24 * 180)
                    await redis.lpush(
                        f"{ns}:log",
                        json.dumps(
                            {
                                "at": _now_iso(),
                                "action": "automation_apply",
                                "rule": rule["id"],
                                "record_id": record["id"],
                                "name": name,
                                "status": status,
                                "due": action_due,
                                "base": m.base,
                            },
                            ensure_ascii=False,
                        ),
                    )
                    await redis.ltrim(f"{ns}:log", 0, 499)
    logger.info("Automation run", base=m.base, mode=m.mode, planned=len(planned))
    return {
        "success": True,
        "mode": m.mode,
        "base": m.base,
        "rules_evaluated": len(rules),
        "records_scanned": len(records),
        "planned": len(planned),
        "actions": planned,
        "note": "Vorschau — nichts geschrieben." if m.mode == "preview" else "Änderungen ausgeführt und protokolliert.",
    }


async def tool_automation_log(m: AutomationLogInput) -> dict[str, Any]:
    logger.info("STEPLOG START automation_log")
    async with redis_client() as (redis, ns):
        raw = await redis.lrange(f"{ns}:log", 0, m.limit - 1)
    entries = []
    for item in raw:
        try:
            entries.append(json.loads(item))
        except Exception:  # noqa: BLE001
            entries.append({"raw": item})
    return {"count": len(entries), "entries": entries}


class AuditListInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=500, description="Anzahl Einträge")
    tool: str | None = Field(default=None, description="Nur Einträge dieses Werkzeugs")
    record_id: str | None = Field(default=None, description="Nur Einträge zu diesem Datensatz")
    actor: str | None = Field(default=None, description="Nur Einträge dieses Aufrufers")


class ErrorLogInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=500, description="Anzahl Einträge")


class AlertsInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=500, description="Anzahl Einträge")


class DataHealthInput(BaseModel):
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    notify: bool = Field(default=False, description="true = Auffälligkeiten als Alarm melden")
    limit: int = Field(default=20, ge=1, le=100, description="Beispiele pro Kategorie")


class AirtableHookRequest(BaseModel):
    record_id: str | None = Field(default=None, description="Datensatz, der die Automation ausgelöst hat")
    record_ids: list[str] | None = Field(default=None, description="Mehrere Datensätze")
    mode: Literal["preview", "apply"] = Field(default="apply")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    event: str | None = Field(default=None, description="Freitext, z.B. Airtable-Automation-Name")


class HookTestInput(BaseModel):
    record_id: str | None = Field(default=None, description="Datensatz für den Test (optional)")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")


class ConfigGetInput(BaseModel):
    pass


class ConfigSetInput(BaseModel):
    alert_webhook_url: str | None = Field(default=None, description="HTTPS-Adresse für Alarme")
    hook_secret: str | None = Field(default=None, description="Gemeinsames Passwort für /hooks/airtable")
    default_base: BaseName | None = Field(default=None, description="Base, wenn ein Aufruf keine nennt")
    clear: list[str] | None = Field(default=None, description="Schlüssel entfernen, z.B. ['alert_webhook_url']")


class TableCreateInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, description="Name der neuen Tabelle")
    fields: list[dict[str, Any]] = Field(..., description="Felder: [{\"name\": \"Name\", \"type\": \"singleLineText\"}]")
    description: str | None = Field(default=None, description="Beschreibung der Tabelle")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    preview: bool = Field(default=True, description="true = nur zeigen, was gesendet würde")
    confirm: bool = Field(default=False, description="Muss true sein, damit die Tabelle entsteht")


class FieldCreateInput(BaseModel):
    table: str = Field(..., description="Tabellenname oder Schlüssel (prijave, casting, tasks)")
    name: str = Field(..., min_length=1, max_length=80, description="Feldname")
    type: str = Field(..., description="Airtable-Feldtyp, z.B. singleLineText, singleSelect, date, number")
    options: dict[str, Any] | None = Field(default=None, description="Optionen, z.B. choices für singleSelect")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    preview: bool = Field(default=True, description="true = nur zeigen, was gesendet würde")
    confirm: bool = Field(default=False, description="Muss true sein, damit wirklich geschrieben wird")


class FieldUpdateInput(BaseModel):
    table: str = Field(..., description="Tabellenname oder Schlüssel")
    field_id: str = Field(..., description="Feld-ID fld…")
    name: str | None = Field(default=None, description="Neuer Name")
    options: dict[str, Any] | None = Field(default=None, description="Neue Optionen (z.B. choices)")
    base: BaseName = Field(default="kopieren", description="Base: kopieren (Standard) oder original")
    preview: bool = Field(default=True, description="true = nur zeigen, was gesendet würde")
    confirm: bool = Field(default=False, description="Muss true sein, damit wirklich geschrieben wird")



async def _read_log(key: str, read: int = 500) -> list[dict[str, Any]]:
    async with redis_client() as (redis, ns):
        raw = await redis.lrange(f"{ns}:{key}", 0, read - 1)
    entries: list[dict[str, Any]] = []
    for item in raw:
        try:
            entries.append(json.loads(item))
        except Exception:  # noqa: BLE001
            entries.append({"raw": item})
    return entries


async def tool_audit_list(m: AuditListInput) -> dict[str, Any]:
    logger.info("STEPLOG START audit_list")
    entries = await _read_log("audit")
    if m.tool:
        entries = [e for e in entries if e.get("tool") == m.tool]
    if m.record_id:
        entries = [e for e in entries if m.record_id in (e.get("record_ids") or [])]
    if m.actor:
        entries = [e for e in entries if str(e.get("actor")) == m.actor]
    return {"count": len(entries[: m.limit]), "total_matching": len(entries), "entries": entries[: m.limit]}


async def tool_error_log(m: ErrorLogInput) -> dict[str, Any]:
    logger.info("STEPLOG START error_log")
    entries = await _read_log("errors")
    return {"count": len(entries[: m.limit]), "total": len(entries), "entries": entries[: m.limit]}


async def tool_alerts_list(m: AlertsInput) -> dict[str, Any]:
    logger.info("STEPLOG START alerts_list")
    entries = await _read_log("alerts")
    return {
        "count": len(entries[: m.limit]),
        "total": len(entries),
        "webhook_configured": bool(await _effective("alert_webhook_url")),
        "entries": entries[: m.limit],
    }


async def tool_data_health(m: DataHealthInput) -> dict[str, Any]:
    logger.info("STEPLOG START data_health")
    briefs = await _records_brief(m.base)
    raw = await _fetch_records(m.base, "prijave", max_records=3000)
    today = _today()
    no_status = [b for b in briefs if not b["status"]]
    no_next_action = [b for b in briefs if not b["next_action"] and b["status"] not in FINAL_STATUSES]
    overdue = [b for b in briefs if b["overdue"]]
    missing = [b for b in briefs if b["missing_documents"]]
    past_appointments = []
    for item in briefs:
        if item["status"] in FINAL_STATUSES:
            continue
        for key in ("casting_date", "visa_date"):
            parsed = _parse_date(item.get(key))
            if parsed and parsed < today:
                past_appointments.append({**item, "field": key, "date": parsed.isoformat()})
    phones: dict[str, list[str]] = {}
    for record in raw:
        fields = record.get("fields") or {}
        digits = _norm_phone(f"{fields.get('Pozivni broj') or ''}{fields.get('Broj telefona') or ''}")
        if len(digits) >= 7:
            phones.setdefault(digits, []).append(_candidate_name(fields) or record["id"])
    duplicates = [{"phone": key, "names": names} for key, names in phones.items() if len(names) > 1]
    issues = (
        len(no_status) + len(no_next_action) + len(overdue) + len(missing)
        + len(past_appointments) + len(duplicates)
    )
    if m.notify and issues:
        await _push_alert(
            "data_health",
            f"{issues} Auffälligkeiten in {BASE_LABEL[m.base]}",
            {
                "base": m.base,
                "ohne_status": len(no_status),
                "ohne_naechste_aktion": len(no_next_action),
                "ueberfaellig": len(overdue),
                "fehlende_unterlagen": len(missing),
                "termine_verpasst": len(past_appointments),
                "doppelte_nummern": len(duplicates),
            },
        )
    return {
        "base": m.base,
        "total": len(briefs),
        "issues": issues,
        "ok": issues == 0,
        "without_status": no_status[: m.limit],
        "without_next_action": no_next_action[: m.limit],
        "overdue_actions": overdue[: m.limit],
        "missing_documents": missing[: m.limit],
        "past_appointments": past_appointments[: m.limit],
        "duplicate_phones": duplicates[: m.limit],
    }


async def _resolve_table_id(base: str, ref: str) -> str:
    if ref in TABLE_NAMES:
        return await _table_id(base, ref)
    for table in await _base_schema(base):
        if table.get("name") == ref or table.get("id") == ref:
            return table["id"]
    raise AirtableError(f"Tabelle '{ref}' wurde in der Base nicht gefunden.", status=404)


async def tool_hook_test(m: HookTestInput) -> dict[str, Any]:
    logger.info("STEPLOG START hook_test")
    secret_set = bool(await _effective("hook_secret"))
    record_id = m.record_id
    if not record_id:
        records = await _fetch_records(m.base, "prijave", max_records=1)
        record_id = records[0]["id"] if records else None
    preview = await tool_automation_run(
        AutomationRunInput(mode="preview", base=m.base, record_ids=[record_id] if record_id else None, limit=300)
    )
    hook_url = "https://runtime.codewords.ai/run/ilvana_airtable_mcp_8b158ec7/hooks/airtable"
    body = {"record_id": record_id or "rec...", "mode": "preview", "event": "Verbindungstest"}
    curl = (
        f"curl -X POST {hook_url} -H 'Content-Type: application/json' "
        + ("-H 'X-Hook-Secret: <dein HOOK_SECRET>' " if secret_set else "")
        + f"-H 'Authorization: Bearer <CODEWORDS_API_KEY>' -d '{json.dumps(body)}'"
    )
    return {
        "ok": True,
        "hook_url": hook_url,
        "secret_configured": secret_set,
        "warning": None
        if secret_set
        else "HOOK_SECRET ist nicht gesetzt — /hooks/airtable ist offen und kann von jedem aufgerufen werden.",
        "headers": {
            "Content-Type": "application/json",
            "X-Hook-Secret": "<HOOK_SECRET>" if secret_set else "(nicht gesetzt)",
            "Authorization": "Bearer <CODEWORDS_API_KEY>",
        },
        "sample_body": body,
        "curl": curl,
        "would_do": preview,
        "note": "Vorschau — es wurde nichts geschrieben.",
    }


async def tool_config_get(m: ConfigGetInput) -> dict[str, Any]:
    logger.info("STEPLOG START config_get")
    config = await _config()
    webhook = await _effective("alert_webhook_url")
    secret = await _effective("hook_secret")
    return {
        "default_base": config.get("default_base") or "kopieren",
        "alert_webhook_url": (webhook[:24] + "…") if webhook else None,
        "alert_webhook_configured": bool(webhook),
        "hook_secret_configured": bool(secret),
        "overrides_in_use": sorted(config.keys()),
        "stored_example_env": {
            "AIRTABLE_PAT": "nur per Platform-Panel, nicht über dieses Werkzeug änderbar",
            "ALERT_WEBHOOK_URL": "kann hier gesetzt werden (config_set)",
            "HOOK_SECRET": "kann hier gesetzt werden (config_set)",
        },
    }


async def tool_config_set(m: ConfigSetInput) -> dict[str, Any]:
    logger.info("STEPLOG START config_set")
    if m.alert_webhook_url and not m.alert_webhook_url.lower().startswith("https://"):
        raise AirtableError("alert_webhook_url muss mit https:// beginnen.")
    if m.hook_secret is not None and 0 < len(m.hook_secret) < 16:
        raise AirtableError("hook_secret muss mindestens 16 Zeichen haben (z.B. openssl rand -hex 32).")
    changes: dict[str, Any] = {
        "alert_webhook_url": m.alert_webhook_url,
        "hook_secret": m.hook_secret,
        "default_base": m.default_base,
    }
    for key in m.clear or []:
        if key not in {"alert_webhook_url", "hook_secret", "default_base"}:
            raise AirtableError(f"Unbekannter Schlüssel '{key}'. Erlaubt: alert_webhook_url, hook_secret, default_base")
        changes[key] = ""
    updated = await _config_save(changes)
    await _append_log(
        "audit",
        {
            "at": _now_iso(),
            "tool": "config_set",
            "actor": _ACTOR.get(),
            "record_ids": [],
            "fields": [k for k, v in changes.items() if v is not None],
            "summary": "Konfiguration geändert",
        },
        2000,
    )
    return {
        "success": True,
        "overrides_in_use": sorted(updated.keys()),
        "alert_webhook_configured": bool((updated.get("alert_webhook_url") or "").strip()),
        "hook_secret_configured": bool((updated.get("hook_secret") or "").strip()),
        "default_base": updated.get("default_base") or "kopieren",
        "note": "Änderungen gelten sofort, kein Redeploy nötig.",
    }


async def tool_table_create(m: TableCreateInput) -> dict[str, Any]:
    logger.info("STEPLOG START table_create")
    if not m.fields:
        raise AirtableError("Mindestens ein Feld angeben (Airtable verlangt ein Primärfeld).")
    base_id = _base_id(m.base)
    payload: dict[str, Any] = {"name": m.name, "fields": m.fields}
    if m.description:
        payload["description"] = m.description
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    if m.preview or not m.confirm:
        return {
            "preview": True,
            "method": "POST",
            "url": url,
            "payload": payload,
            "note": "Nichts gesendet. Zum Anlegen preview=false und confirm=true setzen.",
        }
    result = await _at_request("POST", url, json=payload)
    _schema_cache.pop(base_id, None)
    return {"success": True, "table": result}


async def tool_field_create(m: FieldCreateInput) -> dict[str, Any]:
    logger.info("STEPLOG START field_create")
    base_id = _base_id(m.base)
    table_id = await _resolve_table_id(m.base, m.table)
    payload: dict[str, Any] = {"name": m.name, "type": m.type}
    if m.options:
        payload.update(m.options)
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}/fields"
    if m.preview or not m.confirm:
        return {"preview": True, "method": "POST", "url": url, "payload": payload,
                "note": "Nichts gesendet. Zum Anlegen preview=false und confirm=true setzen."}
    result = await _at_request("POST", url, json=payload)
    _schema_cache.pop(base_id, None)
    return {"success": True, "field": result}


async def tool_field_update(m: FieldUpdateInput) -> dict[str, Any]:
    logger.info("STEPLOG START field_update")
    base_id = _base_id(m.base)
    table_id = await _resolve_table_id(m.base, m.table)
    payload: dict[str, Any] = {}
    if m.name:
        payload["name"] = m.name
    if m.options:
        payload["options"] = m.options
    if not payload:
        raise AirtableError("Nichts zu ändern: name und/oder options angeben.")
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}/fields/{m.field_id}"
    if m.preview or not m.confirm:
        return {"preview": True, "method": "PATCH", "url": url, "payload": payload,
                "note": "Nichts gesendet. Zum Ändern preview=false und confirm=true setzen."}
    result = await _at_request("PATCH", url, json=payload)
    _schema_cache.pop(base_id, None)
    return {"success": True, "field": result}


MODELS: dict[str, Any] = {
    "schema_get": SchemaGetInput,
    "candidates_search": CandidatesSearchInput,
    "applications_search": ApplicationsSearchInput,
    "candidate_dossier": CandidateDossierInput,
    "application_get": ApplicationGetInput,
    "documents_list": DocumentsListInput,
    "casting_ratings_list": CastingRatingsListInput,
    "pipeline_summary": PipelineSummaryInput,
    "due_report": DueReportInput,
    "application_update": ApplicationUpdateInput,
    "application_create": ApplicationCreateInput,
    "applications_bulk_update": BulkUpdateInput,
    "application_add_note": AddNoteInput,
    "casting_rating_upsert": CastingRatingInput,
    "document_upload": DocumentUploadInput,
    "tasks_manage": TasksManageInput,
    "automation_rules": AutomationRulesInput,
    "automation_run": AutomationRunInput,
    "automation_log": AutomationLogInput,
    "audit_list": AuditListInput,
    "error_log": ErrorLogInput,
    "alerts_list": AlertsInput,
    "data_health": DataHealthInput,
    "hook_test": HookTestInput,
    "config_get": ConfigGetInput,
    "config_set": ConfigSetInput,
    "table_create": TableCreateInput,
    "field_create": FieldCreateInput,
    "field_update": FieldUpdateInput,
}

IMPL: dict[str, Any] = {
    "schema_get": tool_schema_get,
    "candidates_search": tool_candidates_search,
    "applications_search": tool_applications_search,
    "candidate_dossier": tool_candidate_dossier,
    "application_get": tool_application_get,
    "documents_list": tool_documents_list,
    "casting_ratings_list": tool_casting_ratings_list,
    "pipeline_summary": tool_pipeline_summary,
    "due_report": tool_due_report,
    "application_update": tool_application_update,
    "application_create": tool_application_create,
    "applications_bulk_update": tool_bulk_update,
    "application_add_note": tool_add_note,
    "casting_rating_upsert": tool_casting_rating_upsert,
    "document_upload": tool_document_upload,
    "tasks_manage": tool_tasks_manage,
    "automation_rules": tool_automation_rules,
    "automation_run": tool_automation_run,
    "automation_log": tool_automation_log,
    "audit_list": tool_audit_list,
    "error_log": tool_error_log,
    "alerts_list": tool_alerts_list,
    "data_health": tool_data_health,
    "hook_test": tool_hook_test,
    "config_get": tool_config_get,
    "config_set": tool_config_set,
    "table_create": tool_table_create,
    "field_create": tool_field_create,
    "field_update": tool_field_update,
}

TOOL_DOCS: dict[str, str] = {
    "schema_get": "Tabellen, Felder, Typen und erlaubte Auswahlwerte einer Base (kopieren|original).",
    "candidates_search": "Kandidaten suchen über Name, Telefon (Handy oder Festnetz), Kundennummer oder Passnummer.",
    "applications_search": "Bewerbungen filtern nach Status, Casting-Gruppe/-Ausgang, Vertrag, Visum, Zeiträumen, überfälligen Aktionen und fehlenden Unterlagen.",
    "candidate_dossier": "Komplette Kandidatenakte als ein JSON: Stammdaten, Prozess, Termine, Dokumente, Bewertungen, Aufgaben, Vorab-Text für einen Anruf.",
    "application_get": "Eine Bewerbung mit allen Feldern und Dokumenten.",
    "documents_list": "Hinterlegte Dateien eines Kandidaten mit Name, Typ, Größe und Link.",
    "casting_ratings_list": "Casting-Bewertungen, optional nur für einen Kandidaten.",
    "pipeline_summary": "Übersicht: Anzahl je Status, überfällige Aktionen, fehlende Unterlagen, Termine der nächsten 7 Tage.",
    "due_report": "Tagesbericht: fällige und überfällige Aktionen, Casting- und Visumtermine, fehlende Unterlagen.",
    "application_update": "Freigegebene Felder einer Bewerbung setzen; optional mit Protokoll-Notiz.",
    "application_create": "Neue Bewerbung anlegen (mindestens 'Ime i prezime'); prüft vorher auf gleiche Telefonnummer und legt nur mit allow_duplicate=true trotzdem an.",
    "applications_bulk_update": "Mehrere Kandidaten gleichzeitig ändern — standardmäßig nur Vorschau, Schreiben erst mit dry_run=false und confirm=true, maximal 50 Datensätze.",
    "application_add_note": "Notiz mit Zeitstempel und Verfasser anhängen (bestehende Notizen bleiben erhalten).",
    "casting_rating_upsert": "Casting-Bewertung anlegen oder aktualisieren, inklusive Verknüpfung zum Kandidaten.",
    "document_upload": "Datei in ein Anhang-Feld hochladen (pdf, jpg, jpeg, png, doc, docx, max. 10 MB).",
    "tasks_manage": "Aufgaben in Table 1 lesen, anlegen oder Status setzen.",
    "automation_rules": "Automatik-Regeln ansehen oder ändern.",
    "automation_run": "Automatik ausführen — preview zeigt nur den Plan, apply schreibt Änderungen und Aufgaben.",
    "automation_log": "Protokoll der Automatik und der Massenänderungen.",
    "audit_list": "Verlauf: wer wann welches Werkzeug auf welchem Datensatz ausgeführt hat (filterbar nach Werkzeug, Datensatz, Aufrufer).",
    "error_log": "Fehlerprotokoll: fehlgeschlagene Aufrufe mit Zeitpunkt, Werkzeug, Aufrufer und Ursache.",
    "alerts_list": "Gespeicherte Alarme (Fehler, Datenauffälligkeiten) und ob ein Alarm-Webhook konfiguriert ist.",
    "data_health": "Qualitätsprüfung: Datensätze ohne Status, ohne nächste Aktion, überfällig, mit fehlenden Unterlagen, verpassten Terminen oder doppelten Telefonnummern.",
    "hook_test": "Testet die Anbindung an Airtable-Automationen: zeigt Hook-URL, Header und was ein Aufruf auslösen würde — ohne etwas zu schreiben.",
    "config_get": "Aktuelle Konfiguration anzeigen: Standard-Base, ob Alarm-Webhook und Hook-Secret gesetzt sind.",
    "config_set": "Konfiguration ändern: Alarm-Webhook, Hook-Secret, Standard-Base — wirkt sofort, ohne Redeploy.",
    "table_create": "Neue Tabelle in der Base anlegen (Vorschau zuerst, echtes Anlegen nur mit confirm).",
    "field_create": "Neues Feld in einer Tabelle anlegen (Vorschau zuerst, echtes Anlegen nur mit confirm).",
    "field_update": "Feld umbenennen oder Auswahlwerte ändern (Vorschau zuerst, echte Änderung nur mit confirm).",
}


async def run_tool(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if name not in IMPL:
        raise AirtableError(f"Unbekanntes Werkzeug '{name}'.", status=404)
    model = MODELS[name]
    actor = _ACTOR.get()
    started = time.time()
    if isinstance(payload, dict) and "base" not in payload and "base" in model.model_fields:
        default_base = (await _config()).get("default_base")
        if default_base:
            payload = {**payload, "base": default_base}
    try:
        parsed = model(**{k: v for k, v in (payload or {}).items() if k in model.model_fields})
    except ValidationError as exc:
        message = f"Ungültige Eingabe für {name}: {exc.errors()[0].get('msg')}"
        await _append_log("errors", {"at": _now_iso(), "tool": name, "actor": actor, "error": message})
        await _push_alert("validation_error", message, {"tool": name})
        raise AirtableError(message) from exc
    try:
        result = await IMPL[name](parsed)
    except AirtableError as exc:
        await _append_log(
            "errors",
            {"at": _now_iso(), "tool": name, "actor": actor, "error": exc.message, "status": exc.status},
        )
        await _push_alert("tool_error", f"{name}: {exc.message}", {"tool": name, "status": exc.status})
        raise
    except Exception as exc:  # noqa: BLE001
        message = f"Interner Fehler in {name}: {type(exc).__name__}: {exc}"
        logger.exception("Tool crashed", tool=name)
        await _append_log("errors", {"at": _now_iso(), "tool": name, "actor": actor, "error": message})
        await _push_alert("tool_crash", message, {"tool": name})
        raise AirtableError(message, status=500) from exc
    if name in WRITE_TOOLS:
        await _append_log(
            "audit",
            {
                "at": _now_iso(),
                "tool": name,
                "actor": actor,
                "base": (payload or {}).get("base", "kopieren"),
                "record_ids": _record_ids_of(result),
                "fields": sorted((payload or {}).get("fields", {}).keys())
                if isinstance((payload or {}).get("fields"), dict)
                else [],
                "duration_s": round(time.time() - started, 2),
                "summary": result.get("note") or result.get("appended") or result.get("matched"),
            },
            2000,
        )
    return result


# ---------------------------------------------------------------- MCP server
fast_app = FastMCP("Ilvana Airtable MCP", json_response=False, stateless_http=True)


async def _mcp(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return await run_tool(name, payload)
    except AirtableError as exc:
        raise McpError(exc.message, code=-32603) from exc


@fast_app.tool()
async def schema_get(
    base: Annotated[str, Field(description="kopieren (Standard) oder original")] = "kopieren",
    include_choices: Annotated[bool, Field(description="Auswahlwerte mitliefern")] = True,
) -> dict[str, Any]:
    """Tabellen, Felder, Typen und erlaubte Auswahlwerte einer Base."""
    return await _mcp("schema_get", {"base": base, "include_choices": include_choices})


@fast_app.tool()
async def candidates_search(
    query: Annotated[str | None, Field(description="Name, Kundennummer oder Passnummer")] = None,
    phone: Annotated[str | None, Field(description="Telefonnummer, beliebiges Format")] = None,
    status: Annotated[str | None, Field(description="Status kandidata (exakt)")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    limit: Annotated[int, Field(description="Treffer pro Seite", ge=1, le=100)] = 25,
) -> dict[str, Any]:
    """Kandidaten über Name, Telefon (Handy oder Festnetz), Kundennummer oder Passnummer suchen."""
    return await _mcp("candidates_search", {"query": query, "phone": phone, "status": status, "base": base, "limit": limit})


@fast_app.tool()
async def applications_search(
    status_kandidata: Annotated[str | None, Field(description="z.B. Casting, Primljeni, Ugovor")] = None,
    casting_grupa: Annotated[str | None, Field(description="UJUTRO oder POPODNE")] = None,
    casting_ishod: Annotated[str | None, Field(description="z.B. Došao, Prošao praktični")] = None,
    ugovor_tok: Annotated[str | None, Field(description="z.B. Potpisan")] = None,
    visa_ishod: Annotated[str | None, Field(description="z.B. Dobio vizu")] = None,
    casting_from: Annotated[str | None, Field(description="Termin casting ab (YYYY-MM-DD)")] = None,
    casting_to: Annotated[str | None, Field(description="Termin casting bis (YYYY-MM-DD)")] = None,
    action_due_before: Annotated[str | None, Field(description="Rok akcije vor (YYYY-MM-DD)")] = None,
    only_overdue: Annotated[bool, Field(description="Nur überfällige Aktionen")] = False,
    only_missing_documents: Annotated[bool, Field(description="Nur unvollständige Unterlagen")] = False,
    query: Annotated[str | None, Field(description="Freitext")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    limit: Annotated[int, Field(description="Treffer pro Seite", ge=1, le=100)] = 25,
    offset: Annotated[int, Field(description="Seiten-Offset", ge=0)] = 0,
) -> dict[str, Any]:
    """Bewerbungen nach Status, Gruppe, Ausgängen, Zeiträumen, überfälligen Aktionen und fehlenden Unterlagen filtern."""
    return await _mcp(
        "applications_search",
        {
            "status_kandidata": status_kandidata,
            "casting_grupa": casting_grupa,
            "casting_ishod": casting_ishod,
            "ugovor_tok": ugovor_tok,
            "visa_ishod": visa_ishod,
            "casting_from": casting_from,
            "casting_to": casting_to,
            "action_due_before": action_due_before,
            "only_overdue": only_overdue,
            "only_missing_documents": only_missing_documents,
            "query": query,
            "base": base,
            "limit": limit,
            "offset": offset,
        },
    )


@fast_app.tool()
async def candidate_dossier(
    record_id: Annotated[str | None, Field(description="Datensatz-ID rec…")] = None,
    query: Annotated[str | None, Field(description="Alternativ: Name")] = None,
    phone: Annotated[str | None, Field(description="Alternativ: Telefonnummer")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Komplette Kandidatenakte als ein JSON — ideal als Vorab-Abruf vor einem Anruf."""
    return await _mcp("candidate_dossier", {"record_id": record_id, "query": query, "phone": phone, "base": base})


@fast_app.tool()
async def application_get(
    record_id: Annotated[str, Field(description="Datensatz-ID rec…")],
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Eine Bewerbung mit allen Feldern und Dokumenten."""
    return await _mcp("application_get", {"record_id": record_id, "base": base})


@fast_app.tool()
async def documents_list(
    record_id: Annotated[str, Field(description="Datensatz-ID rec…")],
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Hinterlegte Dateien eines Kandidaten mit Name, Typ, Größe und Link."""
    return await _mcp("documents_list", {"record_id": record_id, "base": base})


@fast_app.tool()
async def casting_ratings_list(
    candidate_record_id: Annotated[str | None, Field(description="Nur dieser Kandidat")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    limit: Annotated[int, Field(description="Maximale Anzahl", ge=1, le=100)] = 50,
) -> dict[str, Any]:
    """Casting-Bewertungen, optional nur für einen Kandidaten."""
    return await _mcp("casting_ratings_list", {"candidate_record_id": candidate_record_id, "base": base, "limit": limit})


@fast_app.tool()
async def pipeline_summary(
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Anzahl je Status, überfällige Aktionen, fehlende Unterlagen, Termine der nächsten 7 Tage."""
    return await _mcp("pipeline_summary", {"base": base})


@fast_app.tool()
async def due_report(
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    days_ahead: Annotated[int, Field(description="Termine der nächsten X Tage", ge=1, le=60)] = 7,
) -> dict[str, Any]:
    """Tagesbericht mit fälligen Aktionen, Terminen und fehlenden Unterlagen."""
    return await _mcp("due_report", {"base": base, "days_ahead": days_ahead})


@fast_app.tool()
async def application_create(
    fields: Annotated[dict[str, Any], Field(description="Felder des neuen Datensatzes, mindestens 'Ime i prezime'")],
    note: Annotated[str | None, Field(description="Optionaler Startvermerk")] = None,
    allow_duplicate: Annotated[bool, Field(description="Trotz gleicher Telefonnummer anlegen")] = False,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Neue Bewerbung anlegen."""
    return await _mcp("application_create", {"fields": fields, "note": note,
                                            "allow_duplicate": allow_duplicate, "base": base})


@fast_app.tool()
async def application_update(
    record_id: Annotated[str, Field(description="Datensatz-ID rec…")],
    fields: Annotated[dict[str, Any], Field(description="Zu setzende Felder")],
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    note: Annotated[str | None, Field(description="Optionaler Protokoll-Eintrag")] = None,
) -> dict[str, Any]:
    """Freigegebene Felder einer Bewerbung setzen."""
    return await _mcp("application_update", {"record_id": record_id, "fields": fields, "base": base, "note": note})


@fast_app.tool()
async def applications_bulk_update(
    fields: Annotated[dict[str, Any], Field(description="Zu setzende Felder")],
    record_ids: Annotated[list[str] | None, Field(description="Explizite Datensatz-IDs")] = None,
    filter: Annotated[dict[str, Any] | None, Field(description="Filter wie applications_search")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    limit: Annotated[int, Field(description="Maximal 50 Datensätze", ge=1, le=50)] = 50,
    dry_run: Annotated[bool, Field(description="true = nur Vorschau")] = True,
    confirm: Annotated[bool, Field(description="Muss true sein zum Schreiben")] = False,
) -> dict[str, Any]:
    """Mehrere Kandidaten gleichzeitig ändern — Vorschau zuerst, Schreiben nur mit dry_run=false und confirm=true."""
    return await _mcp(
        "applications_bulk_update",
        {
            "fields": fields,
            "record_ids": record_ids,
            "filter": filter,
            "base": base,
            "limit": limit,
            "dry_run": dry_run,
            "confirm": confirm,
        },
    )


@fast_app.tool()
async def application_add_note(
    record_id: Annotated[str, Field(description="Datensatz-ID rec…")],
    note: Annotated[str, Field(description="Notiztext", min_length=1)],
    author: Annotated[str, Field(description="Verfasser")] = "agent",
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Notiz mit Zeitstempel und Verfasser anhängen."""
    return await _mcp("application_add_note", {"record_id": record_id, "note": note, "author": author, "base": base})


@fast_app.tool()
async def casting_rating_upsert(
    fields: Annotated[dict[str, Any], Field(description="Bewertungsfelder")] = {},
    rating_id: Annotated[str | None, Field(description="Vorhandene Bewertung rec…")] = None,
    candidate_record_id: Annotated[str | None, Field(description="Kandidat rec…")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Casting-Bewertung anlegen oder aktualisieren."""
    return await _mcp(
        "casting_rating_upsert",
        {"fields": fields, "rating_id": rating_id, "candidate_record_id": candidate_record_id, "base": base},
    )


@fast_app.tool()
async def document_upload(
    record_id: Annotated[str, Field(description="Datensatz-ID rec…")],
    field: Annotated[str, Field(description="Anhang-Feld, z.B. Lebenslauf")],
    file: Annotated[
        str,
        Field(
            description="Datei (pdf, jpg, jpeg, png, doc, docx) — Adresse des Datei-Uploaders",
            json_schema_extra={"contentMediaType": "application/octet-stream"},
        ),
    ],
    filename: Annotated[str | None, Field(description="Dateiname mit Endung")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    note: Annotated[str | None, Field(description="Optionaler Vermerk")] = None,
) -> dict[str, Any]:
    """Datei hochladen (pdf, jpg, jpeg, png, doc, docx, max. 10 MB)."""
    return await _mcp(
        "document_upload",
        {
            "record_id": record_id,
            "field": field,
            "file": file,
            "filename": filename,
            "base": base,
            "note": note,
        },
    )


@fast_app.tool()
async def tasks_manage(
    action: Annotated[str, Field(description="list, create oder update")] = "list",
    task_id: Annotated[str | None, Field(description="rec… für update")] = None,
    name: Annotated[str | None, Field(description="Aufgabentitel")] = None,
    notes: Annotated[str | None, Field(description="Beschreibung")] = None,
    status: Annotated[str | None, Field(description="Todo, In progress, Done")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    limit: Annotated[int, Field(description="Maximale Anzahl", ge=1, le=100)] = 25,
) -> dict[str, Any]:
    """Aufgaben in Table 1 lesen, anlegen oder Status setzen."""
    return await _mcp(
        "tasks_manage",
        {"action": action, "task_id": task_id, "name": name, "notes": notes, "status": status, "base": base, "limit": limit},
    )


@fast_app.tool()
async def automation_rules(
    action: Annotated[str, Field(description="get oder set")] = "get",
    rules: Annotated[list[dict[str, Any]] | None, Field(description="Regeln bei action=set")] = None,
) -> dict[str, Any]:
    """Automatik-Regeln ansehen oder ändern."""
    return await _mcp("automation_rules", {"action": action, "rules": rules})


@fast_app.tool()
async def automation_run(
    mode: Annotated[str, Field(description="preview oder apply")] = "preview",
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    limit: Annotated[int, Field(description="Maximale Anzahl Datensätze", ge=1, le=1000)] = 300,
    record_ids: Annotated[list[str] | None, Field(description="Optional nur diese Datensätze")] = None,
) -> dict[str, Any]:
    """Automatik ausführen — preview zeigt den Plan, apply schreibt Änderungen und Aufgaben."""
    return await _mcp("automation_run", {"mode": mode, "base": base, "limit": limit, "record_ids": record_ids})


@fast_app.tool()
async def automation_log(
    limit: Annotated[int, Field(description="Anzahl Einträge", ge=1, le=200)] = 25,
) -> dict[str, Any]:
    """Protokoll der Automatik und der Massenänderungen."""
    return await _mcp("automation_log", {"limit": limit})


@fast_app.tool()
async def audit_list(
    limit: Annotated[int, Field(description="Anzahl Einträge", ge=1, le=500)] = 50,
    tool: Annotated[str | None, Field(description="Nur dieses Werkzeug")] = None,
    record_id: Annotated[str | None, Field(description="Nur dieser Datensatz")] = None,
    actor: Annotated[str | None, Field(description="Nur dieser Aufrufer")] = None,
) -> dict[str, Any]:
    """Verlauf: wer wann was geändert hat."""
    return await _mcp("audit_list", {"limit": limit, "tool": tool, "record_id": record_id, "actor": actor})


@fast_app.tool()
async def error_log(
    limit: Annotated[int, Field(description="Anzahl Einträge", ge=1, le=500)] = 50,
) -> dict[str, Any]:
    """Fehlerprotokoll fehlgeschlagener Aufrufe."""
    return await _mcp("error_log", {"limit": limit})


@fast_app.tool()
async def alerts_list(
    limit: Annotated[int, Field(description="Anzahl Einträge", ge=1, le=500)] = 50,
) -> dict[str, Any]:
    """Gespeicherte Alarme und Status des Alarm-Webhooks."""
    return await _mcp("alerts_list", {"limit": limit})


@fast_app.tool()
async def data_health(
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    notify: Annotated[bool, Field(description="Auffälligkeiten als Alarm melden")] = False,
    limit: Annotated[int, Field(description="Beispiele pro Kategorie", ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """Qualitätsprüfung der Daten: Lücken, Fristen, Dubletten."""
    return await _mcp("data_health", {"base": base, "notify": notify, "limit": limit})


@fast_app.tool()
async def hook_test(
    record_id: Annotated[str | None, Field(description="Datensatz für den Test")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
) -> dict[str, Any]:
    """Airtable-Hook testen: URL, Header und geplante Aktionen — ohne zu schreiben."""
    return await _mcp("hook_test", {"record_id": record_id, "base": base})


@fast_app.tool()
async def config_get() -> dict[str, Any]:
    """Aktuelle Konfiguration: Standard-Base, Alarm-Webhook, Hook-Secret."""
    return await _mcp("config_get", {})


@fast_app.tool()
async def config_set(
    alert_webhook_url: Annotated[str | None, Field(description="HTTPS-Adresse für Alarme")] = None,
    hook_secret: Annotated[str | None, Field(description="Mindestens 16 Zeichen")] = None,
    default_base: Annotated[str | None, Field(description="kopieren oder original")] = None,
    clear: Annotated[list[str] | None, Field(description="Schlüssel entfernen")] = None,
) -> dict[str, Any]:
    """Alarm-Webhook, Hook-Secret oder Standard-Base setzen — wirkt sofort."""
    return await _mcp(
        "config_set",
        {"alert_webhook_url": alert_webhook_url, "hook_secret": hook_secret,
         "default_base": default_base, "clear": clear},
    )


@fast_app.tool()
async def table_create(
    name: Annotated[str, Field(description="Name der neuen Tabelle")],
    fields: Annotated[list[dict[str, Any]], Field(description="Feldliste, erstes Feld ist das Primärfeld")],
    description: Annotated[str | None, Field(description="Beschreibung")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    preview: Annotated[bool, Field(description="true = nur zeigen")] = True,
    confirm: Annotated[bool, Field(description="Muss true sein zum Anlegen")] = False,
) -> dict[str, Any]:
    """Neue Tabelle anlegen (Vorschau zuerst)."""
    return await _mcp("table_create", {"name": name, "fields": fields, "description": description,
                                       "base": base, "preview": preview, "confirm": confirm})


@fast_app.tool()
async def field_create(
    table: Annotated[str, Field(description="Tabellenname oder Schlüssel")],
    name: Annotated[str, Field(description="Feldname")],
    type: Annotated[str, Field(description="Airtable-Feldtyp")],
    options: Annotated[dict[str, Any] | None, Field(description="Optionen, z.B. choices")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    preview: Annotated[bool, Field(description="true = nur zeigen")] = True,
    confirm: Annotated[bool, Field(description="Muss true sein zum Anlegen")] = False,
) -> dict[str, Any]:
    """Neues Feld anlegen (Vorschau zuerst)."""
    return await _mcp("field_create", {"table": table, "name": name, "type": type, "options": options,
                                       "base": base, "preview": preview, "confirm": confirm})


@fast_app.tool()
async def field_update(
    table: Annotated[str, Field(description="Tabellenname oder Schlüssel")],
    field_id: Annotated[str, Field(description="Feld-ID fld…")],
    name: Annotated[str | None, Field(description="Neuer Name")] = None,
    options: Annotated[dict[str, Any] | None, Field(description="Neue Optionen")] = None,
    base: Annotated[str, Field(description="kopieren oder original")] = "kopieren",
    preview: Annotated[bool, Field(description="true = nur zeigen")] = True,
    confirm: Annotated[bool, Field(description="Muss true sein zum Ändern")] = False,
) -> dict[str, Any]:
    """Feld umbenennen oder Auswahlwerte ändern (Vorschau zuerst)."""
    return await _mcp("field_update", {"table": table, "field_id": field_id, "name": name, "options": options,
                                       "base": base, "preview": preview, "confirm": confirm})


# ---------------------------------------------------------------- FastAPI app
def create_fastapi_app() -> FastAPI:
    starlette_app = fast_app.streamable_http_app()
    app = FastAPI(
        title="Ilvana Airtable MCP",
        description=(
            "Airtable-Bridge für die Bases 'Ilvana i Hase (Kopieren)' und 'Ilvana i Hase': "
            "Suche, Kandidatenakte, Schreiben, Uploads und Automatik — als MCP-Werkzeuge "
            "und als JSON-HTTP-API."
        ),
        version="1.0.0",
        debug=starlette_app.debug,
        routes=starlette_app.routes,
        middleware=starlette_app.user_middleware,
        lifespan=starlette_app.router.lifespan_context,
    )

    @app.exception_handler(AirtableError)
    async def airtable_error_handler(request: Request, exc: AirtableError) -> JSONResponse:
        logger.warning("Airtable error", path=str(request.url), message=exc.message)
        return JSONResponse(status_code=exc.status, content={"success": False, "error": exc.message})

    @app.middleware("http")
    async def actor_middleware(request: Request, call_next):
        actor = (
            request.headers.get("X-Actor")
            or request.headers.get("Codewords-Caller-Id")
            or request.headers.get("X-Client")
            or "api"
        )
        token = _ACTOR.set(actor[:80])
        try:
            response = await call_next(request)
        finally:
            _ACTOR.reset(token)
        return response

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(content={"status": "ok", "tools": len(MODELS), "bases": BASE_LABEL})

    @app.get("/schema/tools")
    async def tool_definitions() -> JSONResponse:
        tools = []
        for name, model in MODELS.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": TOOL_DOCS.get(name, name),
                        "parameters": model.model_json_schema(),
                    },
                }
            )
        return JSONResponse(content={"tools": tools})

    @app.post("/tools/{tool_name}", response_model=ToolResponse)
    async def call_tool(tool_name: str, request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            payload = {}
        result = await run_tool(tool_name, payload if isinstance(payload, dict) else {})
        return JSONResponse(content={"success": True, "tool": tool_name, "result": result})

    @app.get("/schema")
    async def schema(base: str = "kopieren", include_choices: bool = True) -> JSONResponse:
        return JSONResponse(content=await run_tool("schema_get", {"base": base, "include_choices": include_choices}))

    @app.get("/schema/document")
    async def schema_document(base: str = "kopieren") -> JSONResponse:
        schema = await run_tool("schema_get", {"base": base, "include_choices": True})
        lines = [f"# {schema['base_label']}", "", f"Base-ID: `{schema['base_id']}`", ""]
        for table in schema["tables"]:
            lines.append(f"## {table['table']}")
            lines.append(f"Tabellen-ID: `{table['table_id']}` · {len(table['fields'])} Felder")
            lines.append("")
            lines.append("| Feld | Typ | schreibbar | Auswahl |")
            lines.append("|---|---|---|---|")
            for field in table["fields"]:
                choices = ", ".join(field.get("choices") or []) or "—"
                lines.append(
                    f"| {field['name']} | {field['type']} | {'ja' if field['writable'] else 'nein'} | {choices} |"
                )
            lines.append("")
        return JSONResponse(content={"base": base, "markdown": "\n".join(lines)})

    @app.post("/automation/daily")
    async def automation_daily(base: str = "kopieren", mode: str = "preview") -> JSONResponse:
        report = await run_tool("due_report", {"base": base, "days_ahead": 7})
        run = await run_tool("automation_run", {"mode": mode, "base": base, "limit": 500})
        health = await run_tool("data_health", {"base": base, "notify": True, "limit": 20})
        logger.info("Daily automation finished", base=base, mode=mode, planned=run.get("planned"), issues=health.get("issues"))
        return JSONResponse(content={"report": report, "automation": run, "health": health})

    @app.post("/hooks/airtable")
    async def airtable_hook(request: Request) -> JSONResponse:
        secret = await _effective("hook_secret")
        if secret and request.headers.get("X-Hook-Secret") != secret:
            return JSONResponse(status_code=401, content={"success": False, "error": "Ungültiges Hook-Secret"})
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        payload = AirtableHookRequest(**body) if isinstance(body, dict) else AirtableHookRequest()
        if payload.mode == "apply" and not secret:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "HOOK_SECRET ist nicht gesetzt — 'apply' ist gesperrt. "
                    "Setze ein Secret über config_set oder nutze mode=preview.",
                },
            )
        ids = payload.record_ids or ([payload.record_id] if payload.record_id else None)
        token = _ACTOR.set("airtable-automation")
        try:
            run = await run_tool(
                "automation_run",
                {"mode": payload.mode, "base": payload.base, "record_ids": ids, "limit": 300},
            )
        finally:
            _ACTOR.reset(token)
        logger.info("Airtable automation hook", event=payload.event, planned=run.get("planned"))
        return JSONResponse(content={"success": True, "event": payload.event, "automation": run})

    @app.post("/hooks/airtable/test")
    async def airtable_hook_test(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        record_id = body.get("record_id") if isinstance(body, dict) else None
        base = body.get("base", "kopieren") if isinstance(body, dict) else "kopieren"
        result = await run_tool("hook_test", {"record_id": record_id, "base": base})
        return JSONResponse(content=result)

    @app.post("/", response_model=RootResponse)
    async def root(payload: RootRequest) -> JSONResponse:
        if payload.tool:
            result = await run_tool(payload.tool, payload.arguments)
            return JSONResponse(content={"success": True, "tool": payload.tool, "result": result})
        return JSONResponse(
            content={
                "success": True,
                "service": "Ilvana Airtable MCP",
                "tools": list(MODELS),
                "usage": "POST /tools/<name> mit JSON-Body, oder MCP unter /mcp/",
            }
        )

    return app


if __name__ == "__main__":
    run_service(create_fastapi_app())
