"""CompanyMemory version chain — never overwrite silently."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_delta_engine.schema import VERSION as DELTA_ENGINE_VERSION
from knowledge_delta_engine.util import checksum, memory_fingerprint


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store():
    from knowledge_factory.historical_depth import store as hd_store

    return hd_store


def load_current(entity: str) -> dict[str, Any] | None:
    try:
        return _store().get_object("company_memory", entity.upper())
    except Exception:
        return None


def load_version(entity: str, version: int) -> dict[str, Any] | None:
    try:
        return _store().get_object("company_memory_version", f"{entity.upper()}@v{version}")
    except Exception:
        return None


def list_versions(entity: str) -> list[dict[str, Any]]:
    try:
        meta = _store().get_object("company_memory_meta", entity.upper()) or {}
        return list(meta.get("versions") or [])
    except Exception:
        return []


def next_version_number(entity: str) -> int:
    versions = list_versions(entity)
    if not versions:
        return 1
    return int(max(v.get("version") or 0 for v in versions)) + 1


def persist_versioned(
    memory: dict[str, Any],
    *,
    reason: str,
    memory_delta: dict[str, Any] | None = None,
    force_new: bool = False,
) -> dict[str, Any]:
    """
    Persist CompanyMemory as Current + append-only version object.

    If fingerprint matches Current and not force_new → no new version (deterministic no-op).
    """
    entity = str(memory.get("entity") or "").upper()
    if not entity:
        return {"written": False, "reason": "missing_entity"}

    hd = _store()
    current = load_current(entity)
    fp = memory_fingerprint(memory)
    prior_fp = memory_fingerprint(current) if isinstance(current, dict) else None

    if current and prior_fp == fp and not force_new:
        meta = hd.get_object("company_memory_meta", entity) or {}
        return {
            "written": False,
            "noop": True,
            "entity": entity,
            "version": meta.get("current_version"),
            "checksum": fp,
            "reason": "identical_evidence_deterministic_noop",
        }

    ver = next_version_number(entity)
    compiled_at = memory.get("compiled_at") or _now()
    envelope = {
        "version": ver,
        "compiled_at": compiled_at,
        "sources": memory.get("lineage") or [],
        "checksum": fp,
        "compiler_version": memory.get("version"),
        "delta_engine_version": DELTA_ENGINE_VERSION,
        "reason": reason,
        "coverage_pct": (memory.get("coverage") or {}).get("coverage_pct"),
        "delta_summary": (memory_delta or {}).get("summary"),
    }

    versioned = {
        **memory,
        "memory_version": ver,
        "version_envelope": envelope,
        "memory_delta": memory_delta,
        "previous_version": (current or {}).get("memory_version"),
        "previous_checksum": prior_fp,
    }

    # Append-only version object
    hd.put_object("company_memory_version", f"{entity}@v{ver}", versioned)
    # Current pointer (living object — intentional current replace with full audit trail in versions)
    hd.put_object("company_memory", entity, versioned)

    meta = hd.get_object("company_memory_meta", entity) or {
        "entity": entity,
        "kind": "company_memory_meta",
        "versions": [],
    }
    versions = list(meta.get("versions") or [])
    versions.append(envelope)
    meta.update(
        {
            "current_version": ver,
            "current_checksum": fp,
            "updated_at": _now(),
            "versions": versions[-200:],
        }
    )
    hd.put_object("company_memory_meta", entity, meta)

    # Series breadcrumb
    try:
        from knowledge_factory.historical_depth.schema import pit_record

        as_of = compiled_at[:10]
        hd.put_series(
            "company_memory",
            entity,
            [
                pit_record(
                    entity=entity,
                    kind="company_memory_version",
                    period=f"v{ver}",
                    period_end=as_of,
                    available_from=as_of,
                    payload=envelope,
                    source="knowledge_delta_engine",
                    confidence=float(memory.get("confidence") or 0.8),
                )
            ],
        )
    except Exception:
        pass

    return {
        "written": True,
        "noop": False,
        "entity": entity,
        "version": ver,
        "checksum": fp,
        "previous_version": envelope.get("reason") and (current or {}).get("memory_version"),
        "reason": reason,
    }
