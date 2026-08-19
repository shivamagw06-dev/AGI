"""Persist valuation company packs to Supabase (read model).

Python remains the calculation engine. Node serves the latest stored pack so
page loads do not recompute terminal packs on every request.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional
from urllib import error, request

SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "valuation_company_pack_v1"
ALLOWED_WINDOWS = ("1Y", "3Y", "5Y", "10Y", "MAX")
FRESH_SECONDS = 15 * 60
AGING_SECONDS = 60 * 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat().replace("+00:00", "Z")


def _credentials() -> Optional[tuple[str, str]]:
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    return url, key


def _rest(
    method: str,
    table: str,
    *,
    query: str = "",
    body: Any = None,
    prefer: str = "return=representation",
    timeout_seconds: float = 20.0,
) -> Any:
    creds = _credentials()
    if not creds:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for valuation packs.")
    url, key = creds
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = request.Request(
        f"{url}/rest/v1/{table}{query}",
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
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Valuation pack Supabase {method} {table} failed ({exc.code}): {detail}") from exc


def freshness_for_age(age_seconds: float) -> str:
    if age_seconds <= FRESH_SECONDS:
        return "fresh"
    if age_seconds <= AGING_SECONDS:
        return "aging"
    return "stale"


def normalize_window(window: str | None) -> str:
    value = str(window or "5Y").strip().upper()
    return value if value in ALLOWED_WINDOWS else "5Y"


def build_data_quality(payload: dict[str, Any]) -> dict[str, Any]:
    dq = payload.get("data_quality") if isinstance(payload.get("data_quality"), dict) else {}
    freshness = dq.get("freshness") if isinstance(dq.get("freshness"), dict) else {}
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    health = payload.get("health_score") if isinstance(payload.get("health_score"), dict) else {}
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    return {
        "validated": bool(dq.get("validated")),
        "warnings": len(dq.get("warnings") or []),
        "missing": len(dq.get("missing") or []),
        "conflicts": int(dq.get("conflicts") or 0),
        "overrides": int(dq.get("overrides") or 0),
        "coverage_pct": coverage.get("pct"),
        "health_score": health.get("score"),
        "health_band": health.get("band") or overview.get("data_quality"),
        "price_age_hours": freshness.get("price_age_hours"),
        "ratio_age_hours": freshness.get("ratio_age_hours"),
        "financial_age_hours": freshness.get("financial_age_hours"),
    }


def persist_company_pack(
    payload: dict[str, Any],
    *,
    window: str = "5Y",
    peer_limit: int = 12,
) -> dict[str, Any]:
    """Write one company pack to history + latest pointer."""
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise ValueError("Valuation pack snapshot requires a successful company pack.")

    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("Valuation pack snapshot requires symbol.")

    win = normalize_window(window or payload.get("window"))
    generated_at = _iso()
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    source_as_of = (
        overview.get("updated")
        or (provenance.get("price") or {}).get("updated_at")
        or generated_at[:10]
    )
    if isinstance(source_as_of, str) and "T" in source_as_of:
        source_as_of = source_as_of[:10]

    quality = build_data_quality(payload)
    health = payload.get("health_score") if isinstance(payload.get("health_score"), dict) else {}

    envelope = {
        **payload,
        "generated_at": generated_at,
        "source_as_of": source_as_of,
        "status": "ready",
        "freshness": "fresh",
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "snapshot_data_quality": quality,
        "read_model": "supabase_valuation_company_pack",
    }

    inserted = _rest(
        "POST",
        "valuation_company_packs",
        body={
            "symbol": symbol,
            "pack_window": win,
            "peer_limit": max(1, min(int(peer_limit or 12), 40)),
            "generated_at": generated_at,
            "source_as_of": str(source_as_of),
            "status": "ready",
            "freshness": "fresh",
            "schema_version": SCHEMA_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "engine": payload.get("engine") or "unified_valuation_engine",
            "engine_version": str(payload.get("version") or "3.0"),
            "data_quality": quality,
            "health_score": health.get("score"),
            "health_band": health.get("band") or overview.get("data_quality"),
            "coverage_pct": quality.get("coverage_pct"),
            "price_age_hours": quality.get("price_age_hours"),
            "ratio_age_hours": quality.get("ratio_age_hours"),
            "payload": envelope,
        },
        prefer="return=representation",
    )
    if not isinstance(inserted, list) or not inserted:
        raise RuntimeError("Valuation pack insert returned no row.")
    row = inserted[0]
    pack_id = row["id"]

    _rest(
        "POST",
        "valuation_company_packs_latest?on_conflict=symbol,pack_window",
        body={
            "symbol": symbol,
            "pack_window": win,
            "pack_id": pack_id,
            "generated_at": generated_at,
            "source_as_of": str(source_as_of),
            "status": "ready",
            "freshness": "fresh",
            "schema_version": SCHEMA_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "data_quality": quality,
            "health_score": health.get("score"),
            "payload": envelope,
            "updated_at": generated_at,
        },
        prefer="resolution=merge-duplicates,return=minimal",
    )

    deleted = 0
    try:
        url, key = _credentials() or ("", "")
        if url and key:
            req = request.Request(
                f"{url}/rest/v1/rpc/cleanup_valuation_company_packs",
                data=json.dumps({"retention_days": 30}).encode("utf-8"),
                method="POST",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            with request.urlopen(req, timeout=8.0) as response:
                raw = response.read()
                deleted = int(json.loads(raw)) if raw else 0
    except Exception:
        deleted = 0

    return {
        "ok": True,
        "pack_id": pack_id,
        "symbol": symbol,
        "window": win,
        "pack_window": win,
        "generated_at": generated_at,
        "source_as_of": str(source_as_of),
        "status": "ready",
        "freshness": "fresh",
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "data_quality": quality,
        "cleaned_up": deleted,
    }


def compute_and_persist(
    symbol: str,
    *,
    window: str = "5Y",
    peer_limit: int = 12,
) -> dict[str, Any]:
    """Run company_pack once and store the read model."""
    from valuation_engine.terminal import company_pack

    ticker = str(symbol or "").strip().upper()
    win = normalize_window(window)
    capped = max(1, min(int(peer_limit or 12), 40))
    payload = company_pack(ticker, window=win, peer_limit=capped)
    if not isinstance(payload, dict) or not payload.get("ok"):
        return {
            "ok": False,
            "symbol": ticker,
            "window": win,
            "error": (payload or {}).get("error") if isinstance(payload, dict) else "company_pack_failed",
            "status": "failed",
        }
    meta = persist_company_pack(payload, window=win, peer_limit=capped)
    enriched = {
        **payload,
        **{
            k: meta[k]
            for k in (
                "generated_at",
                "source_as_of",
                "status",
                "freshness",
                "schema_version",
                "calculation_version",
            )
            if k in meta
        },
        "snapshot_data_quality": meta.get("data_quality"),
        "read_model": "supabase_valuation_company_pack",
    }
    return {**meta, "payload": enriched}


def latest_pack_row(symbol: str, *, window: str = "5Y") -> Optional[dict[str, Any]]:
    ticker = str(symbol or "").strip().upper()
    win = normalize_window(window)
    if not ticker:
        return None
    rows = _rest(
        "GET",
        "valuation_company_packs_latest",
        query=(
            f"?symbol=eq.{ticker}&pack_window=eq.{win}"
            "&select=pack_id,symbol,pack_window,generated_at,source_as_of,status,freshness,"
            "schema_version,calculation_version,data_quality,health_score,payload"
        ),
        body=None,
        prefer="return=representation",
    )
    if isinstance(rows, list) and rows:
        row = rows[0]
        # Keep API-facing alias used by the terminal payload.
        if "window" not in row and row.get("pack_window"):
            row = {**row, "window": row["pack_window"]}
        return row
    return None


def serve_company_pack(
    symbol: str,
    *,
    window: str = "5Y",
    peer_limit: int = 12,
    refresh: bool = False,
) -> dict[str, Any]:
    """HTTP GET path: stored pack only. Live warehouse compute stays on POST /snapshot."""
    if refresh:
        from valuation_engine.terminal import company_pack

        return company_pack(
            symbol,
            window=window,
            peer_limit=max(1, min(int(peer_limit or 12), 40)),
        )
    ticker = str(symbol or "").strip().upper()
    try:
        row = latest_pack_row(ticker, window=window)
    except Exception:
        row = None
    payload = row.get("payload") if isinstance(row, dict) else None
    if isinstance(payload, dict) and payload.get("ok") is not False:
        return {
            **payload,
            "ok": True,
            "symbol": ticker or payload.get("symbol"),
            "read_model": "supabase_valuation_company_pack",
            "generated_at": row.get("generated_at") or payload.get("generated_at"),
            "freshness": row.get("freshness") or payload.get("freshness") or "unknown",
        }
    return {
        "ok": False,
        "symbol": ticker,
        "window": normalize_window(window),
        "error": "NO_VALUATION_PACK_YET",
        "read_model": "supabase_valuation_company_pack",
    }


def list_aging_latest(*, limit: int = 8, max_age_seconds: int | None = None) -> list[dict[str, Any]]:
    """Return latest packs older than fresh band for scheduler refresh."""
    threshold = max_age_seconds if max_age_seconds is not None else FRESH_SECONDS
    cutoff = _iso(datetime.fromtimestamp(_now().timestamp() - threshold, tz=timezone.utc))
    capped = max(1, min(int(limit or 8), 25))
    rows = _rest(
        "GET",
        "valuation_company_packs_latest",
        query=(
            f"?status=eq.ready&generated_at=lt.{cutoff}"
            "&select=symbol,pack_window,generated_at,freshness,pack_id"
            f"&order=generated_at.asc&limit={capped}"
        ),
        body=None,
        prefer="return=representation",
    )
    if not isinstance(rows, list):
        return []
    return [{**row, "window": row.get("pack_window") or row.get("window")} for row in rows]
