"""Replay a stored Evaluation Lab result and detect regressions."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.golden_universe.per_ticker import evaluate_ticker
from institutional_evaluation_lab.golden_universe.schema import REPLAY_COMPARE_FIELDS
from institutional_evaluation_lab.golden_universe import store as golden_store


def _num_close(a: Any, b: Any, *, tol: float = 0.15) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a) == str(b)


def _price_runner_from_stored(stored: dict[str, Any]):
    snap = ((stored.get("replay_inputs") or {}).get("price_snapshot")) or {}
    if not snap and stored.get("price_ltp") is not None:
        snap = {
            "ltp": stored.get("price_ltp"),
            "as_of": stored.get("market_snapshot"),
            "stale": bool(stored.get("price_stale")),
            "source_provider": stored.get("price_source") or "groww",
        }

    def _runner(ticker: str, force: bool = False) -> dict[str, Any]:
        return {
            "refreshed": False,
            "reason": "replay_injected_snapshot",
            "snapshot": snap,
            "age_sec": 0,
            "provider_called": "replay",
        }

    return _runner


def compare_replay(stored: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    for field in REPLAY_COMPARE_FIELDS:
        a = stored.get(field)
        b = replayed.get(field)
        if field in {"recommendation_readiness", "company_quality", "financial_quality", "valuation"}:
            ok = _num_close(a, b)
        else:
            ok = str(a or "") == str(b or "")
        if not ok:
            mismatches.append({"field": field, "stored": a, "replayed": b})
    return {
        "matched": len(mismatches) == 0,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def replay_ticker(
    *,
    release_id: str,
    ticker: str,
    ide_runner=None,
) -> dict[str, Any]:
    """
    Re-run one ticker using the stored market snapshot for determinism.

    If replay does not reproduce the stored decision/gate/readiness, report regression.
    """
    packed = golden_store.load_release_results(release_id)
    if not packed:
        return {"ok": False, "error": "release_not_found", "release_id": release_id}
    t = ticker.upper()
    stored = next((r for r in (packed.get("rows") or []) if str(r.get("ticker")).upper() == t), None)
    if not stored:
        # Try loading file directly if rows_sample path was used
        from pathlib import Path
        import json

        path = Path(packed["results_dir"]) / f"{t}.json"
        if path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
        else:
            return {"ok": False, "error": "ticker_not_found", "release_id": release_id, "ticker": t}

    meta = {
        "ticker": t,
        "name": stored.get("company_name"),
        "sector": stored.get("sector"),
        "bucket": stored.get("bucket"),
    }
    query = ((stored.get("replay_inputs") or {}).get("query")) or f"Should I buy {t}?"
    price_runner = _price_runner_from_stored(stored)

    replayed = evaluate_ticker(
        meta,
        query=query,
        price_runner=price_runner,
        ide_runner=ide_runner,
        force_price_refresh=False,
    )
    comparison = compare_replay(stored, replayed)
    return {
        "ok": comparison["matched"],
        "release_id": release_id,
        "ticker": t,
        "regression": not comparison["matched"],
        "comparison": comparison,
        "stored": {k: stored.get(k) for k in REPLAY_COMPARE_FIELDS},
        "replayed": {k: replayed.get(k) for k in REPLAY_COMPARE_FIELDS},
        "replayed_timing": replayed.get("timing"),
        "versions": packed.get("manifest"),
        "note": (
            "Replay injects the stored Groww/market snapshot so price drift does not "
            "create false regressions. Decision/gate mismatches are real regressions."
        ),
    }


def replay_release(
    *,
    release_id: str,
    limit: int | None = None,
    ide_runner=None,
) -> dict[str, Any]:
    packed = golden_store.load_release_results(release_id)
    if not packed:
        return {"ok": False, "error": "release_not_found", "release_id": release_id}
    tickers = list(packed.get("manifest", {}).get("tickers") or [r.get("ticker") for r in packed.get("rows") or []])
    if limit is not None:
        tickers = tickers[: max(1, int(limit))]
    rows = []
    regressions = 0
    for t in tickers:
        if not t:
            continue
        row = replay_ticker(release_id=release_id, ticker=str(t), ide_runner=ide_runner)
        rows.append(row)
        if row.get("regression"):
            regressions += 1
    return {
        "ok": regressions == 0,
        "release_id": release_id,
        "n": len(rows),
        "regressions": regressions,
        "pass_pct": round(100.0 * (len(rows) - regressions) / (len(rows) or 1), 1),
        "rows": rows,
    }
