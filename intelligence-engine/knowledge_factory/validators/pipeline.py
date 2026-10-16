"""Validation rules — reject missing/duplicate/conflicting/stale/placeholder."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_factory.schema import ALLOWED_SOURCES

VALIDATION_VERSION = "kf-validation-v1.0.0"
PLACEHOLDERS = {None, "", "n/a", "na", "none", "null", "-", "--", 0, 0.0}


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def resolve_entity(entity: str | None, aliases: dict[str, str] | None = None) -> dict[str, Any]:
    aliases = aliases or {
        "INFY.NS": "INFY",
        "TCS.NS": "TCS",
        "WIPRO.NS": "WIPRO",
        "RELIANCE.NS": "RELIANCE",
        "HDFCBANK.NS": "HDFCBANK",
    }
    if not entity:
        return {"ok": False, "entity": None, "confidence": 0.0, "reason": "missing_entity"}
    e = str(entity).upper().strip()
    e = aliases.get(e, e.replace(".NS", "").replace(".BO", ""))
    return {"ok": True, "entity": e, "confidence": 0.95 if e.isalpha() or e.isalnum() else 0.7}


def check_freshness(timestamp: str | None, *, max_age_hours: float = 72.0) -> dict[str, Any]:
    ts = _parse_ts(timestamp)
    if ts is None:
        return {"ok": False, "freshness_hours": None, "reason": "missing_timestamp"}
    age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
    return {
        "ok": age_h <= max_age_hours,
        "freshness_hours": round(age_h, 3),
        "reason": None if age_h <= max_age_hours else "stale",
    }


def check_completeness(payload: dict[str, Any] | None, required: tuple[str, ...] = ()) -> dict[str, Any]:
    payload = payload or {}
    missing = [k for k in required if k not in payload or payload.get(k) in PLACEHOLDERS]
    return {"ok": not missing, "missing": missing, "coverage": round(1.0 - len(missing) / max(len(required), 1), 4)}


def check_provenance(dataset: dict[str, Any]) -> dict[str, Any]:
    src = str(dataset.get("source") or (dataset.get("provenance") or {}).get("source") or "")
    if src not in ALLOWED_SOURCES:
        return {"ok": False, "reason": f"source_not_allowed:{src}"}
    if not dataset.get("timestamp") and not (dataset.get("provenance") or {}).get("collected_at"):
        return {"ok": False, "reason": "missing_provenance_timestamp"}
    return {"ok": True, "source": src}


def check_consistency(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    reasons: list[str] = []
    # Conflicting PE primitives
    if payload.get("eps") is not None and float(payload.get("eps") or 0) <= 0 and payload.get("force_pe") is not None:
        reasons.append("conflict_negative_eps_with_pe")
    if payload.get("duplicate_of"):
        reasons.append("duplicate")
    if payload.get("conflict"):
        reasons.append("conflicting_data")
    # Impossible PE
    pe = payload.get("pe")
    if isinstance(pe, (int, float)) and pe < 0:
        reasons.append("impossible_negative_pe")
    return {"ok": not reasons, "reasons": reasons}


def validate_dataset(
    dataset: dict[str, Any],
    *,
    required_fields: tuple[str, ...] = (),
    max_age_hours: float = 72.0,
    allow_stale: bool = False,
) -> dict[str, Any]:
    entity = resolve_entity(dataset.get("entity"))
    prov = check_provenance(dataset)
    fresh = check_freshness(dataset.get("timestamp") or (dataset.get("provenance") or {}).get("collected_at"), max_age_hours=max_age_hours)
    complete = check_completeness(dataset.get("payload") or dataset, required_fields)
    consistent = check_consistency(dataset.get("payload") or dataset)

    reasons: list[str] = []
    if not entity["ok"]:
        reasons.append(entity["reason"])
    if not prov["ok"]:
        reasons.append(prov["reason"])
    if not fresh["ok"] and not allow_stale:
        reasons.append(fresh["reason"] or "stale")
    if not complete["ok"]:
        reasons.append("incomplete:" + ",".join(complete["missing"]))
    if not consistent["ok"]:
        reasons.extend(consistent["reasons"])

    quality = 95.0
    if reasons:
        quality = 20.0
    elif fresh.get("freshness_hours") and fresh["freshness_hours"] > 24:
        quality = 82.0

    return {
        "validation_version": VALIDATION_VERSION,
        "ok": not reasons,
        "rejected": bool(reasons),
        "reject_reasons": reasons,
        "entity": entity.get("entity"),
        "entity_confidence": entity.get("confidence"),
        "freshness_hours": fresh.get("freshness_hours"),
        "coverage": complete.get("coverage"),
        "quality": quality,
        "source": prov.get("source") or dataset.get("source"),
        "published": not reasons,
    }


def dedupe_filings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        key = str(r.get("filing_id") or r.get("id") or r.get("title") or "") + "|" + str(r.get("date") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
