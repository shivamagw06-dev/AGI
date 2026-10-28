"""Persist Hedge Fund Lab terminal snapshots to Supabase (read model).

Python remains the calculation engine. Node serves the stored snapshot so page
loads do not re-run warehouse scanners on every request.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional
from urllib import error, parse, request

SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "hfl_terminal_v2"
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
    timeout_seconds: float = 12.0,
) -> Any:
    creds = _credentials()
    if not creds:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for HFL snapshots.")
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
        raise RuntimeError(f"HFL snapshot Supabase {method} {table} failed ({exc.code}): {detail}") from exc


def freshness_for_age(age_seconds: float) -> str:
    if age_seconds <= FRESH_SECONDS:
        return "fresh"
    if age_seconds <= AGING_SECONDS:
        return "aging"
    return "stale"


def build_data_quality(payload: dict[str, Any]) -> dict[str, Any]:
    hero = payload.get("hero") if isinstance(payload.get("hero"), dict) else {}
    regime = payload.get("regime") if isinstance(payload.get("regime"), dict) else {}
    cards = payload.get("cards") if isinstance(payload.get("cards"), list) else []
    universe_meta = regime.get("universe_meta") or hero.get("universe_meta") or {}
    card_counts = {
        str(card.get("id") or ""): int(card.get("count") or 0)
        for card in cards
        if isinstance(card, dict) and card.get("id")
    }
    return {
        "universe_scanned": int(hero.get("universe_scanned") or regime.get("universe") or 0),
        "live_opportunities": int(hero.get("live_opportunities") or 0),
        "companies_flagged": int(hero.get("companies_flagged") or 0),
        "cards_with_results": sum(1 for count in card_counts.values() if count > 0),
        "card_counts": card_counts,
        "regime_stance": regime.get("stance"),
        "universe_source": (universe_meta or {}).get("source"),
        "factors_joined": (universe_meta or {}).get("factors_joined"),
    }


def flatten_opportunities(snapshot_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in payload.get("cards") or []:
        if not isinstance(card, dict):
            continue
        scan_id = str(card.get("id") or "").strip().lower()
        if not scan_id:
            continue
        label = card.get("label")
        for index, item in enumerate(card.get("results") or [], start=1):
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker") or (item.get("long_leg") or {}).get("ticker") or "").upper()
            if not ticker:
                continue
            rows.append(
                {
                    "snapshot_id": snapshot_id,
                    "scan_id": scan_id,
                    "scan_label": label,
                    "ticker": ticker,
                    "company_name": item.get("company_name") or (item.get("long_leg") or {}).get("company_name"),
                    "sector": item.get("sector") or (item.get("long_leg") or {}).get("sector"),
                    "rank": index,
                    "confidence": item.get("confidence"),
                    "why": item.get("why"),
                    "row_payload": item,
                }
            )
    return rows


def persist_terminal_snapshot(payload: dict[str, Any], *, limit_used: int = 12) -> dict[str, Any]:
    """Write one complete terminal payload + flattened opportunities."""
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise ValueError("HFL snapshot requires a successful terminal payload.")

    generated_at = _iso()
    source_as_of = str(payload.get("as_of") or generated_at[:10])
    quality = build_data_quality(payload)
    hero = payload.get("hero") if isinstance(payload.get("hero"), dict) else {}

    envelope = {
        **payload,
        "generated_at": generated_at,
        "source_as_of": source_as_of,
        "status": "ready",
        "freshness": "fresh",
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "data_quality": quality,
        "read_model": "supabase_hfl_terminal",
    }

    inserted = _rest(
        "POST",
        "hfl_terminal_snapshots",
        body={
            "generated_at": generated_at,
            "source_as_of": source_as_of,
            "status": "ready",
            "freshness": "fresh",
            "schema_version": SCHEMA_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "data_quality": quality,
            "limit_used": int(limit_used),
            "universe_scanned": int(quality.get("universe_scanned") or 0),
            "live_opportunities": int(quality.get("live_opportunities") or hero.get("live_opportunities") or 0),
            "payload": envelope,
        },
        prefer="return=representation",
    )
    if not isinstance(inserted, list) or not inserted:
        raise RuntimeError("HFL snapshot insert returned no row.")
    snapshot = inserted[0]
    snapshot_id = snapshot["id"]

    opportunities = flatten_opportunities(snapshot_id, payload)
    if opportunities:
        # Chunk to stay under PostgREST payload limits.
        chunk = 200
        for start in range(0, len(opportunities), chunk):
            _rest(
                "POST",
                "hfl_terminal_opportunities",
                body=opportunities[start : start + chunk],
                prefer="return=minimal",
            )

    deleted = 0
    try:
        # Best-effort history cleanup (30 days).
        url, key = _credentials() or ("", "")
        if url and key:
            req = request.Request(
                f"{url}/rest/v1/rpc/cleanup_hfl_terminal_snapshots",
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
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "source_as_of": source_as_of,
        "status": "ready",
        "freshness": "fresh",
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "opportunities": len(opportunities),
        "cleaned_up": deleted,
        "data_quality": quality,
    }


def compute_and_persist(*, limit: int = 12) -> dict[str, Any]:
    """Run the live terminal once and store the read model."""
    from hedge_fund_lab.terminal import overview

    capped = max(1, min(int(limit or 12), 50))
    payload = overview(limit=capped)
    if not isinstance(payload, dict) or not payload.get("ok"):
        return {
            "ok": False,
            "error": (payload or {}).get("error") if isinstance(payload, dict) else "overview_failed",
            "status": "failed",
        }
    meta = persist_terminal_snapshot(payload, limit_used=capped)
    return {**meta, "payload": {**payload, **{k: meta[k] for k in (
        "generated_at", "source_as_of", "status", "freshness",
        "schema_version", "calculation_version", "data_quality",
    ) if k in meta}}}


def latest_snapshot_row() -> Optional[dict[str, Any]]:
    rows = _rest(
        "GET",
        "hfl_terminal_snapshots",
        query="?status=eq.ready&select=id,generated_at,source_as_of,status,freshness,schema_version,calculation_version,data_quality,limit_used,universe_scanned,live_opportunities,payload&order=generated_at.desc&limit=1",
        body=None,
        prefer="return=representation",
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def serve_terminal_overview(*, limit: int = 12, refresh: bool = False) -> dict[str, Any]:
    """HTTP GET path: stored snapshot only. Live warehouse scans stay on POST /snapshot."""
    if refresh:
        from hedge_fund_lab.terminal import overview

        return overview(limit=max(1, min(int(limit or 12), 50)))
    try:
        row = latest_snapshot_row()
    except Exception:
        row = None
    payload = row.get("payload") if isinstance(row, dict) else None
    if isinstance(payload, dict) and (payload.get("cards") is not None or payload.get("ok")):
        served = {
            **payload,
            "ok": payload.get("ok", True),
            "read_model": "supabase_hfl_terminal",
            "generated_at": row.get("generated_at") or payload.get("generated_at"),
            "source_as_of": row.get("source_as_of") or payload.get("source_as_of") or payload.get("as_of"),
            "freshness": row.get("freshness") or payload.get("freshness") or "unknown",
        }
        try:
            from hedge_fund_lab.live_prices import overlay_live_prices_on_payload

            served = overlay_live_prices_on_payload(served)
        except Exception:
            pass
        return served
    return {
        "ok": True,
        "status": "warming",
        "freshness": "unavailable",
        "read_model": "supabase_hfl_terminal",
        "cards": [],
        "overlap": [],
        "research_queue": [],
        "hero": {"universe_scanned": 0, "live_opportunities": 0, "companies_flagged": 0},
        "policy": "Serving the stored research snapshot. Request-time warehouse scans are disabled.",
    }
