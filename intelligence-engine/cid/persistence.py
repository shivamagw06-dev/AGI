"""Durable Supabase versions for generated CID dossiers."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any
from urllib import error, parse, request

TABLE = "cid_company_dossier_versions"


def _credentials() -> tuple[str, str] | None:
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return (url, key) if url and key else None


def _rest(method: str, query: str = "", body: Any = None, *, prefer: str = "return=representation") -> Any:
    creds = _credentials()
    if not creds:
        return None
    url, key = creds
    data = None if body is None else json.dumps(body, default=str).encode("utf-8")
    req = request.Request(
        f"{url}/rest/v1/{TABLE}{query}",
        data=data,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except (error.HTTPError, error.URLError, TimeoutError):
        return None


def load_latest(ticker: str) -> dict[str, Any] | None:
    t = str(ticker or "").upper()
    if not t:
        return None
    query = (
        f"?ticker=eq.{parse.quote(t)}&select=dossier,version,generated_at"
        "&order=version.desc&limit=1"
    )
    rows = _rest("GET", query)
    if not isinstance(rows, list) or not rows:
        return None
    dossier = rows[0].get("dossier")
    if not isinstance(dossier, dict):
        return None
    dossier["persisted_version"] = rows[0].get("version")
    return dossier


def save_version(dossier: dict[str, Any]) -> dict[str, Any]:
    t = str(dossier.get("ticker") or "").upper()
    if not t or not _credentials():
        return {"persisted": False, "reason": "supabase_not_configured"}
    latest = _rest(
        "GET",
        f"?ticker=eq.{parse.quote(t)}&select=version&order=version.desc&limit=1",
    )
    version = int((latest or [{}])[0].get("version") or 0) + 1
    generated = dossier.get("dossier_generation") or {}
    row = {
        "id": str(uuid.uuid4()),
        "ticker": t,
        "company_name": (dossier.get("identity") or {}).get("company_name") or t,
        "version": version,
        "generator_version": generated.get("generator_version"),
        "model": generated.get("model"),
        "generated_at": generated.get("generated_at"),
        "coverage_score": dossier.get("coverage_score"),
        "coverage_grade": dossier.get("coverage_grade"),
        "dossier": dossier,
    }
    saved = _rest("POST", "", row)
    return {"persisted": bool(saved), "version": version if saved else None}
