"""Framework / sector / macro / portfolio / decision scorecards."""

from __future__ import annotations

from typing import Any

from decision_quality import store as idq_store
from decision_quality.metrics.compute import compute_decision_metrics


def _avg(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 2) if xs else 0.0


def _decision_metrics_list(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for d in decisions:
        m = compute_decision_metrics(d)
        if not m.get("insufficient"):
            out.append({"decision": d, "metrics": m["metrics"]})
    return out


def build_framework_scorecards(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    by_fw: dict[str, list[dict[str, Any]]] = {}
    for d in decisions:
        fw = str(d.get("primary_framework") or "unknown")
        by_fw.setdefault(fw, []).append(d)

    cards = {}
    for fw, rows in sorted(by_fw.items()):
        scored = _decision_metrics_list(rows)
        outcomes = [1.0 if r["decision"].get("prediction_correct") else 0.0 for r in scored]
        errors = [
            abs(
                float((r["decision"].get("outcome_graph") or {}).get("realised_return") or 0)
                - float((r["decision"].get("outcome_graph") or {}).get("expected_return") or 0)
            )
            for r in scored
        ]
        sector_perf: dict[str, list[float]] = {}
        regime_perf: dict[str, list[float]] = {}
        failure_modes: dict[str, int] = {}
        for r in scored:
            d = r["decision"]
            acc = 1.0 if d.get("prediction_correct") else 0.0
            sector_perf.setdefault(str(d.get("sector")), []).append(acc)
            regime_perf.setdefault(str(d.get("macro_regime")), []).append(acc)
            for fm in d.get("failure_modes") or []:
                failure_modes[fm] = failure_modes.get(fm, 0) + 1
        confs = [float(d.get("confidence") or 0) for d in rows if (d.get("outcome_graph") or {}).get("available")]
        n_ok = sum(1 for o in outcomes if o >= 1.0)
        card = {
            "framework": fw,
            "uses": len(rows),
            "uses_with_outcome": len(scored),
            "success_rate": round(n_ok / max(1, len(scored)), 4) if scored else 0.0,
            "success_rate_pct": round(100.0 * n_ok / max(1, len(scored)), 2) if scored else 0.0,
            "average_error": _avg(errors),
            "sector_performance": {k: _avg(v) for k, v in sector_perf.items()},
            "regime_performance": {k: _avg(v) for k, v in regime_perf.items()},
            "confidence": _avg(confs),
            "failure_modes": failure_modes,
            "average_framework_success_rate": _avg(
                [float(r["metrics"]["framework_success_rate"]) for r in scored]
            ),
            "fabricated": False,
        }
        cards[fw] = card
        idq_store.put_scorecard("framework", fw, card)

    payload = {"kind": "framework", "n": len(cards), "scorecards": cards, "fabricated": False}
    idq_store.put_scorecard("framework", "_index", payload)
    return payload


def build_sector_scorecards(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    by_sec: dict[str, list[dict[str, Any]]] = {}
    for d in decisions:
        by_sec.setdefault(str(d.get("sector") or "unknown"), []).append(d)

    cards = {}
    for sector, rows in sorted(by_sec.items()):
        scored = _decision_metrics_list(rows)
        qualities = [float(r["metrics"]["decision_accuracy"]) for r in scored]
        pred = [1.0 if r["decision"].get("prediction_correct") else 0.0 for r in scored]
        fw_perf: dict[str, list[float]] = {}
        errors: list[str] = []
        for r in scored:
            fw = str(r["decision"].get("primary_framework"))
            fw_perf.setdefault(fw, []).append(1.0 if r["decision"].get("prediction_correct") else 0.0)
            errors.extend(list(r["decision"].get("failure_modes") or []))
        confs = [float(d.get("confidence") or 0) for d in rows if (d.get("outcome_graph") or {}).get("available")]
        card = {
            "sector": sector,
            "decision_count": len(rows),
            "decisions_with_outcome": len(scored),
            "average_quality": _avg(qualities),
            "prediction_accuracy": _avg([p * 100 for p in pred]) if pred else 0.0,
            "framework_performance": {k: round(_avg(v), 4) for k, v in fw_perf.items()},
            "typical_errors": sorted(set(errors)),
            "confidence": _avg(confs),
            "fabricated": False,
        }
        cards[sector] = card
        idq_store.put_scorecard("sector", sector, card)

    payload = {"kind": "sector", "n": len(cards), "scorecards": cards, "fabricated": False}
    idq_store.put_scorecard("sector", "_index", payload)
    return payload


def build_macro_scorecards(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    by_reg: dict[str, list[dict[str, Any]]] = {}
    for d in decisions:
        by_reg.setdefault(str(d.get("macro_regime") or "unknown"), []).append(d)

    cards = {}
    for regime, rows in sorted(by_reg.items()):
        scored = _decision_metrics_list(rows)
        pred = [1.0 if r["decision"].get("prediction_correct") else 0.0 for r in scored]
        fw_scores: dict[str, list[float]] = {}
        outcomes = []
        for r in scored:
            fw = str(r["decision"].get("primary_framework"))
            acc = 1.0 if r["decision"].get("prediction_correct") else 0.0
            fw_scores.setdefault(fw, []).append(acc)
            og = r["decision"].get("outcome_graph") or {}
            outcomes.append(
                {
                    "decision_id": r["decision"].get("decision_id"),
                    "alpha": og.get("alpha"),
                    "drawdown": og.get("drawdown"),
                    "action": (r["decision"].get("portfolio") or {}).get("action"),
                }
            )
        fw_avg = {k: _avg(v) for k, v in fw_scores.items()}
        ranked = sorted(fw_avg.items(), key=lambda kv: -kv[1])
        card = {
            "macro_regime": regime,
            "decision_count": len(rows),
            "decisions_with_outcome": len(scored),
            "average_accuracy": _avg([p * 100 for p in pred]) if pred else 0.0,
            "best_frameworks": [k for k, v in ranked if v >= 0.5][:3],
            "worst_frameworks": [k for k, v in sorted(fw_avg.items(), key=lambda kv: kv[1]) if v < 0.5][:3],
            "framework_accuracy": fw_avg,
            "portfolio_outcomes": outcomes,
            "fabricated": False,
        }
        cards[regime] = card
        idq_store.put_scorecard("macro", regime, card)

    payload = {"kind": "macro", "n": len(cards), "scorecards": cards, "fabricated": False}
    idq_store.put_scorecard("macro", "_index", payload)
    return payload


def build_portfolio_scorecard(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    scored = _decision_metrics_list(decisions)
    sizing = [float(r["metrics"]["portfolio_quality"]) for r in scored]
    alphas = [
        float((r["decision"].get("outcome_graph") or {}).get("alpha") or 0)
        for r in scored
    ]
    drawdowns = [
        float((r["decision"].get("outcome_graph") or {}).get("drawdown") or 0)
        for r in scored
    ]
    pred = [1.0 if r["decision"].get("prediction_correct") else 0.0 for r in scored]
    sector_weights: dict[str, int] = {}
    for d in decisions:
        sector_weights[str(d.get("sector"))] = sector_weights.get(str(d.get("sector")), 0) + 1
    risk_q = [float(r["metrics"]["risk_quality"]) for r in scored]
    scenario_q = [float(r["metrics"]["scenario_accuracy"]) for r in scored]

    # Tracking error proxy: stdev of alpha
    te = 0.0
    if len(alphas) >= 2:
        mean = sum(alphas) / len(alphas)
        te = (sum((a - mean) ** 2 for a in alphas) / (len(alphas) - 1)) ** 0.5

    card = {
        "kind": "portfolio",
        "position_sizing_quality": _avg(sizing),
        "sector_allocation": sector_weights,
        "risk_allocation": {"average_risk_quality": _avg(risk_q)},
        "scenario_quality": _avg(scenario_q),
        "drawdown": {"average": _avg(drawdowns), "worst": round(min(drawdowns), 4) if drawdowns else 0.0},
        "portfolio_alpha": {"average": _avg(alphas), "sum": round(sum(alphas), 4) if alphas else 0.0},
        "tracking_error": round(te, 4),
        "decision_accuracy": _avg([p * 100 for p in pred]) if pred else 0.0,
        "n_decisions": len(decisions),
        "n_with_outcome": len(scored),
        "fabricated": False,
    }
    idq_store.put_scorecard("portfolio", "aggregate", card)
    return card


def build_decision_scorecards(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    cards = {}
    for d in decisions:
        m = compute_decision_metrics(d)
        card = {
            "decision_id": d.get("decision_id"),
            "entity": d.get("entity"),
            "metrics": m.get("metrics") or {},
            "insufficient": bool(m.get("insufficient")),
            "reason": m.get("reason"),
            "fabricated": False,
        }
        cards[str(d.get("decision_id"))] = card
        idq_store.put_scorecard("decision", str(d.get("decision_id")), card)
    payload = {"kind": "decision", "n": len(cards), "scorecards": cards, "fabricated": False}
    idq_store.put_scorecard("decision", "_index", payload)
    return payload


def build_all_scorecards(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "decision": build_decision_scorecards(decisions),
        "framework": build_framework_scorecards(decisions),
        "sector": build_sector_scorecards(decisions),
        "macro": build_macro_scorecards(decisions),
        "portfolio": build_portfolio_scorecard(decisions),
        "observability_only": True,
        "fabricated": False,
    }
