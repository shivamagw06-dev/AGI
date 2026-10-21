"""Point-in-time evidence retrieval — future leakage forbidden."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.store import get_pack


def replay_evidence(
    *,
    question: str,
    as_of: str,
    ticker_hint: str | None = None,
) -> dict[str, Any]:
    """Retrieve evidence with available_from <= as_of only."""
    from evidence_retrieval.pipeline import retrieve_evidence

    out = retrieve_evidence(question, ticker_hint=ticker_hint, as_of=as_of)
    day = str(as_of)[:10]
    leaked = [
        r.get("evidence_id")
        for r in (out.get("ranked") or [])
        if str(r.get("available_from") or "")[:10] > day
    ]
    out["replay"] = {
        "as_of": day,
        "future_leakage": bool(leaked),
        "leaked_ids": leaked,
        "ok": not leaked,
        "deterministic": True,
    }
    return out


def replay_pack(pack_id: str) -> dict[str, Any] | None:
    pack = get_pack(pack_id)
    if not pack:
        return None
    return {**pack, "replay": True, "fabricated": False}


def validate_no_future_leakage(pack_or_run: dict[str, Any], as_of: str) -> dict[str, Any]:
    day = str(as_of)[:10]
    items = pack_or_run.get("items") or pack_or_run.get("ranked") or []
    leaked = [
        i.get("evidence_id")
        for i in items
        if str(i.get("available_from") or "")[:10] > day
    ]
    return {"as_of": day, "future_leakage": bool(leaked), "leaked_ids": leaked, "ok": not leaked}


__all__ = ["replay_evidence", "replay_pack", "validate_no_future_leakage"]
