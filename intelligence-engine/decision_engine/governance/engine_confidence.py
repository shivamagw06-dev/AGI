"""Per-engine confidence — Decision Engine can weight by weakest evidence."""

from __future__ import annotations

from typing import Any

from decision_engine.governance.schema import ENGINE_KEYS, IMPACT_RANK


def _pct(*vals: Any, default: float = 0.0) -> float:
    for v in vals:
        if v is None:
            continue
        try:
            n = float(v)
        except (TypeError, ValueError):
            continue
        if n <= 1.5:
            n *= 100.0
        return max(0.0, min(100.0, n))
    return float(default)


def build_engine_confidence(
    *,
    readiness_gate: dict[str, Any] | None = None,
    layers: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    layers = layers if isinstance(layers, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cov = gate.get("coverage") or {}
    cards = {c.get("key"): c for c in (gate.get("diagnostic_cards") or []) if isinstance(c, dict)}
    bq = ca.get("business_quality") or {}
    fin = ca.get("financial_intelligence") or {}

    engines = {
        "business": _pct(
            (layers.get("company_quality") or {}).get("score"),
            bq.get("coverage_pct"),
            default=_pct(bq.get("business_quality_score"), default=40),
        ),
        "financial": _pct(
            (layers.get("financial_quality") or {}).get("evidence_quality_score"),
            cov.get("financials"),
            fin.get("coverage_pct"),
            default=0,
        ),
        "valuation": _pct(cov.get("valuation"), (layers.get("valuation") or {}).get("score"), default=0),
        "ownership": _pct(cov.get("ownership"), default=0),
        "macro": _pct(cov.get("macro"), (layers.get("macro") or {}).get("score"), default=0),
        "technical": _pct(cov.get("technicals"), (layers.get("technical") or {}).get("score"), default=0),
        "news_catalysts": _pct(cov.get("news"), cov.get("filings"), default=0),
        "research": _pct(cov.get("research"), default=0),
    }
    # Freshness / presence adjustments
    for key, card_key in (
        ("financial", "financials"),
        ("ownership", "ownership"),
        ("valuation", "valuation"),
        ("technical", "technicals"),
        ("news_catalysts", "filings"),
    ):
        card = cards.get(card_key) or {}
        if card.get("status") == "outdated":
            engines[key] = min(engines[key], 55.0)
        elif card.get("status") in {"missing", "not_ingested"}:
            engines[key] = min(engines[key], 25.0)

    board = [
        {"engine": k, "label": k.replace("_", " ").title(), "confidence_pct": round(engines[k], 1)}
        for k in ENGINE_KEYS
    ]
    weakest = sorted(board, key=lambda r: r["confidence_pct"])[:3]
    weakest_pct = weakest[0]["confidence_pct"] if weakest else 0.0
    # Governance weighting hint: never overweight above weakest hard pillar
    hard = [engines["financial"], engines["valuation"], engines["ownership"], engines["business"]]
    hard_floor = min(hard) if hard else weakest_pct

    return {
        "engines": board,
        "by_engine": {r["engine"]: r["confidence_pct"] for r in board},
        "weakest": weakest,
        "weakest_engine": (weakest[0]["engine"] if weakest else None),
        "weakest_confidence_pct": weakest_pct,
        "hard_evidence_floor_pct": round(hard_floor, 1),
        "weighting_rule": (
            "Decision Engine should not issue high conviction above the weakest hard evidence pillar "
            "(business / financial / valuation / ownership)."
        ),
        "note": "Per-engine confidence — completeness/reliability of each intelligence input.",
    }


def rank_critical_missing(
    *,
    readiness_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rank missing evidence by expected impact for ingestion priority."""
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    cards = list(gate.get("diagnostic_cards") or gate.get("checklist") or [])
    critical: list[dict[str, Any]] = []
    for c in cards:
        if not isinstance(c, dict) or c.get("present"):
            continue
        impact = str(c.get("expected_impact") or "Medium")
        # Elevate filings/financials/ownership when missing
        key = str(c.get("key") or "")
        if key in {"financials", "filings", "ownership"} and impact == "High":
            impact = "Very High"
        critical.append(
            {
                "rank": 0,
                "label": c.get("label"),
                "key": key,
                "status": c.get("status"),
                "impact": impact,
                "required": list(c.get("required") or [])[:4],
                "latest_available": c.get("latest_available"),
                "why_it_matters": c.get("why_it_matters") or "",
            }
        )
    critical.sort(key=lambda r: (-IMPACT_RANK.get(str(r.get("impact")), 0), str(r.get("label"))))
    for i, row in enumerate(critical, start=1):
        row["rank"] = i
    return {
        "items": critical[:10],
        "top_priority": (critical[0] if critical else None),
        "ingestion_hint": (
            [str(x.get("label")) for x in critical[:5]] if critical else []
        ),
        "note": "Critical missing evidence ranked for collectors and operators.",
    }
