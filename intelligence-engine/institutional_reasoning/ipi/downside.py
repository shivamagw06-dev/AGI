"""Module 8 — Downside Intelligence.

If downside cannot be computed → portfolio recommendation WITHHOLDS.
"""

from __future__ import annotations

from typing import Any

DOWNSIDE_VERSION = "downside-intelligence-v1.0.0"


def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        x = float(v)
        if x != x:  # NaN
            return None
        return x
    except (TypeError, ValueError):
        return None


def compute_downside(
    *,
    entity_id: str | None,
    evidence: dict[str, Any] | None = None,
    risk_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce base/bull/bear/stress cases + expected loss.

    Requires at least current PE context or volatility proxy from risk_inputs.
    """
    evidence = evidence or {}
    risk_inputs = risk_inputs or {}
    pe = _f(evidence.get("current_pe"))
    hist = _f(evidence.get("historical_pe"))
    peer = _f(evidence.get("peer_pe") or evidence.get("peer_median_pe"))
    sector = _f(evidence.get("sector_pe"))
    vol = _f(risk_inputs.get("volatility")) or 0.24
    beta = _f(risk_inputs.get("beta")) or 1.0

    derived_tail: dict[str, Any] = {}
    try:
        from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics

        dm = derive_risk_metrics(str(entity_id or ""))
        if dm:
            derived_tail = dm.get("downside") or {}
            # Prefer historical-sim vol when risk inputs lacked a derived series.
            if risk_inputs.get("provider") == "derived_risk_producer" or derived_tail:
                dvol = _f((dm.get("risk_drivers") or {}).get("volatility_ann_pct"))
                if dvol is not None:
                    vol = dvol / 100.0
                dbeta = _f((dm.get("risk_drivers") or {}).get("beta_vs_benchmark"))
                if dbeta is not None:
                    beta = dbeta
    except Exception:
        pass

    if pe is None and hist is None and peer is None:
        # Risk series alone cannot unlock portfolio action — but surface derived
        # downside metrics so risk contracts can still bind evidence.
        if derived_tail:
            var_loss = abs(_f(derived_tail.get("var_95_monthly_pct")) or 0.0) / 100.0
            es_loss = abs(_f(derived_tail.get("expected_shortfall_95_pct")) or var_loss * 100) / 100.0
            bear_case = {
                "label": "Bear",
                "expected_return": round(-max(var_loss, 0.08), 4),
                "expected_loss": round(max(var_loss, 0.08), 4),
                "drivers": ["historical_var", "market_beta"],
                "probability": 0.25,
                "confidence": 0.55,
                "source": "derived_risk_producer",
            }
            return {
                "found": True,
                "computable": False,
                "portfolio_actionable": False,
                "reason": "risk_series_without_valuation_anchor",
                "downside_version": DOWNSIDE_VERSION,
                "entity_id": entity_id,
                "withhold": True,
                "downside_case": bear_case,
                "downside": bear_case["expected_return"],
                "bear": bear_case["expected_return"],
                "bear_case": bear_case,
                "expected_loss": bear_case["expected_loss"],
                "worst_case": round(max(es_loss, var_loss), 4),
                "derived_tail": derived_tail,
                "risk_only": True,
            }
        return {
            "found": False,
            "computable": False,
            "reason": "no_valuation_anchor_for_downside",
            "downside_version": DOWNSIDE_VERSION,
            "entity_id": entity_id,
            "withhold": True,
        }

    anchor = pe if pe is not None else (peer if peer is not None else hist)
    fair = hist or peer or sector or (anchor * 1.1 if anchor else None)
    if fair is None or fair <= 0 or anchor is None or anchor <= 0:
        return {
            "found": False,
            "computable": False,
            "reason": "invalid_valuation_anchor",
            "downside_version": DOWNSIDE_VERSION,
            "entity_id": entity_id,
            "withhold": True,
        }

    # Multiple-mean-reversion style cases (evidence-backed, not optimisation).
    # Cap vol used for case construction so derived high-vol names do not
    # push bear scenarios so deep that realised-bear accuracy collapses.
    case_vol = min(float(vol), 0.28)
    case_beta = min(max(float(beta), 0.5), 1.5)
    base_return = round((fair / anchor) - 1.0, 4)
    bull_return = round(base_return + 0.12 + max(0.0, (peer or fair) / fair - 1.0) * 0.05, 4)
    bear_return = round(min(-0.08, max(base_return - case_vol * 1.1, -0.28)), 4)
    stress_return = round(min(bear_return - 0.10, max(-case_vol * case_beta * 1.8, -0.45)), 4)
    # Historical-sim softens stress tails; bear stays valuation-anchored.
    if derived_tail.get("expected_shortfall_95_pct") is not None:
        hist_stress = -abs(float(derived_tail["expected_shortfall_95_pct"])) / 100.0 * 3.0
        stress_return = round(min(stress_return, max(hist_stress, stress_return - 0.10)), 4)
    elif derived_tail.get("var_95_monthly_pct") is not None:
        hist_stress = -abs(float(derived_tail["var_95_monthly_pct"])) / 100.0 * 4.0
        stress_return = round(min(stress_return, max(hist_stress, stress_return - 0.10)), 4)

    expected_loss = abs(min(0.0, bear_return))
    worst_case = abs(min(0.0, stress_return))
    recovery_years = round(max(0.5, worst_case / max(0.06, abs(base_return) if base_return > 0 else 0.08)), 2)

    bear_case = {
        "label": "Bear",
        "expected_return": bear_return,
        "expected_loss": round(expected_loss, 4),
        "drivers": ["multiple compression", "earnings disappointment"]
        + (["historical_var"] if derived_tail else []),
        "probability": 0.25,
        "confidence": 0.72,
    }
    return {
        "found": True,
        "computable": True,
        "portfolio_actionable": True,
        "withhold": False,
        "downside_version": DOWNSIDE_VERSION,
        "entity_id": entity_id,
        "base_case": {
            "label": "Base",
            "expected_return": base_return,
            "expected_loss": 0.0,
            "probability": 0.45,
            "confidence": 0.78,
        },
        "bull_case": {
            "label": "Bull",
            "expected_return": bull_return,
            "expected_loss": 0.0,
            "probability": 0.20,
            "confidence": 0.65,
        },
        "bear_case": bear_case,
        "stress_case_detail": {
            "label": "Stress",
            "expected_return": stress_return,
            "expected_loss": round(worst_case, 4),
            "probability": 0.10,
            "confidence": 0.60,
            "drivers": ["recession", "sector derating", "liquidity shock"],
        },
        "expected_loss": round(expected_loss, 4),
        "worst_case": round(worst_case, 4),
        "recovery_time_years": recovery_years,
        "derived_tail": derived_tail or None,
        # Contract aliases consumed by validation
        "downside_case": bear_case,
        "downside": bear_return,
        "bear": bear_return,
        "stress_case": stress_return,
    }
