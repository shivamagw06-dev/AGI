"""External baseline comparison harness.

Compares AGIB derived metrics / decisions to an explicit external baseline
fixture (never silently invents market consensus). Soft eval only.
"""

from __future__ import annotations

from typing import Any

BASELINE_VERSION = "external-baseline-v1.0.0"

# Explicit fixture baselines — replace with vendor feeds in production.
_BASELINES: dict[str, dict[str, Any]] = {
    "INFY": {
        "provider": "fixture_consensus",
        "trailing_pe": 26.5,
        "historical_pe_10y": 23.0,
        "beta": 0.95,
        "volatility_ann": 0.22,
    },
    "TCS": {
        "provider": "fixture_consensus",
        "trailing_pe": 29.0,
        "historical_pe_10y": 26.0,
        "beta": 0.88,
        "volatility_ann": 0.20,
    },
}


def compare_entity(ticker: str) -> dict[str, Any]:
    t = ticker.upper()
    base = _BASELINES.get(t)
    if not base:
        return {
            "baseline_version": BASELINE_VERSION,
            "ticker": t,
            "found": False,
            "reason": "no_external_baseline_fixture",
        }

    from institutional_reasoning.fundamentals.production import derive_latest
    from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics

    pe = derive_latest(t, "PE")
    risk = derive_risk_metrics(t) or {}
    drivers = risk.get("risk_drivers") or {}

    rows = []

    def _row(metric: str, ours: float | None, theirs: float | None, tol: float) -> None:
        if ours is None or theirs is None:
            rows.append({"metric": metric, "ours": ours, "baseline": theirs, "ok": False, "reason": "missing"})
            return
        gap = abs(ours - theirs)
        rows.append(
            {
                "metric": metric,
                "ours": round(ours, 4),
                "baseline": round(theirs, 4),
                "abs_gap": round(gap, 4),
                "ok": gap <= tol,
                "tolerance": tol,
            }
        )

    pe_v = pe.get("value") if isinstance(pe, dict) else None
    _row("trailing_pe", float(pe_v) if pe_v is not None else None, float(base["trailing_pe"]), 4.0)
    beta = drivers.get("beta_vs_benchmark")
    _row("beta", float(beta) if beta is not None else None, float(base["beta"]), 0.25)
    vol = drivers.get("volatility_ann_pct")
    _row(
        "volatility_ann",
        float(vol) / 100.0 if vol is not None else None,
        float(base["volatility_ann"]),
        0.12,
    )

    return {
        "baseline_version": BASELINE_VERSION,
        "ticker": t,
        "found": True,
        "provider": base["provider"],
        "rows": rows,
        "passed": all(r.get("ok") for r in rows),
        "note": "Fixture baseline only — not a live vendor feed.",
    }


def run_baseline_suite(tickers: list[str] | None = None) -> dict[str, Any]:
    tickers = tickers or list(_BASELINES)
    results = [compare_entity(t) for t in tickers]
    return {
        "baseline_version": BASELINE_VERSION,
        "n": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "results": results,
        "gate_passed": all(r.get("passed") or not r.get("found") for r in results if r.get("found")),
    }
