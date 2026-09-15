"""Incremental compile — never rebuild CompanyMemory from scratch when unchanged."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_delta_engine.diff import build_memory_delta
from knowledge_delta_engine.ledger import append_ledger
from knowledge_delta_engine.util import memory_fingerprint
from knowledge_delta_engine.versioning import load_current, persist_versioned


def incremental_compile(
    ticker: str,
    *,
    force: bool = False,
    persist: bool = True,
    skip_live: bool = False,
    allow_live_prices: bool = True,
    injected: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Compile only what changed since last successful CompanyMemory.

    Steps:
      1. Load prior CompanyMemory (Current)
      2. Compile candidate memory (reuse company_memory compiler)
      3. Build memory_delta
      4. If identical → deterministic noop (return prior + empty delta)
      5. Else version + ledger append
    """
    from company_memory.production import compile as memory_compile
    from company_memory.resolve import resolve_ticker

    t0 = datetime.now(timezone.utc)
    entity = resolve_ticker(ticker)
    prior = load_current(entity)

    candidate = memory_compile(
        entity,
        force=force,
        persist=False,  # delta engine owns versioning
        skip_live=skip_live,
        allow_live_prices=allow_live_prices,
        injected=injected,
        use_cache=False,
    )

    delta = build_memory_delta(prior if isinstance(prior, dict) else None, candidate)
    identical = bool(delta.get("identical_to_prior")) or (
        prior is not None and memory_fingerprint(prior) == memory_fingerprint(candidate)
    )

    if identical and not force:
        out = {
            **(prior or candidate),
            "enabled": True,
            "incremental": True,
            "rebuilt": False,
            "noop": True,
            "memory_delta": {
                **delta,
                "status": "UNCHANGED",
                "summary": "Recompiling identical evidence — no unnecessary changes.",
            },
            "delta_engine": {
                "applied": True,
                "version_written": False,
                "reason": "identical_evidence",
            },
            "latency_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
        }
        return out

    # First compile or material change
    compile_reason = reason or (
        "initial_compile" if prior is None else f"delta:{delta.get('n_field_changes', 0)}_fields"
    )
    store_result = None
    ledger_result = None
    if persist and candidate.get("ok"):
        store_result = persist_versioned(
            candidate,
            reason=compile_reason,
            memory_delta=delta,
            force_new=force,
        )
        if store_result.get("written"):
            ledger_result = append_ledger(entity, delta, candidate)
        # Reload current for version fields
        current = load_current(entity) or candidate
    else:
        current = {
            **candidate,
            "memory_version": (prior or {}).get("memory_version"),
            "memory_delta": delta,
        }

    return {
        **current,
        "enabled": True,
        "incremental": prior is not None,
        "rebuilt": prior is None or force,
        "noop": bool(store_result and store_result.get("noop")),
        "memory_delta": delta,
        "delta_engine": {
            "applied": True,
            "version_written": bool(store_result and store_result.get("written")),
            "store": store_result,
            "ledger": ledger_result,
            "reason": compile_reason,
            "prior_version": (prior or {}).get("memory_version"),
        },
        "latency_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
    }
