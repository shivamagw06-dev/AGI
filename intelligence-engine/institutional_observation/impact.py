"""Impact engine — which entities / reasons / decisions / forecasts are affected."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

from institutional_observation.classifier import ClassifiedChange
from institutional_observation.detector import CompanySnapshot


@dataclass(frozen=True)
class ImpactAssessment:
    affected_companies: tuple[str, ...]
    affected_entities: tuple[str, ...]
    affected_reasons: tuple[str, ...]
    affected_decisions: tuple[str, ...]
    affected_forecasts: tuple[str, ...]
    affected_portfolios: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "affected_companies": list(self.affected_companies),
            "affected_entities": list(self.affected_entities),
            "affected_reasons": list(self.affected_reasons),
            "affected_decisions": list(self.affected_decisions),
            "affected_forecasts": list(self.affected_forecasts),
            "affected_portfolios": list(self.affected_portfolios),
        }


_REASON_MAP = {
    "valuation": ("valuation", "bottom_line", "institutional_view"),
    "overall_risk": ("risk_assessment", "bear_case", "bottom_line"),
    "financial_quality": ("financial_quality", "investment_thesis", "bottom_line"),
    "business_quality": ("business_quality", "investment_thesis", "bottom_line"),
    "confidence": ("confidence", "bottom_line"),
    "recommendation": ("institutional_view", "bottom_line"),
    "rbi_repo_cut": ("investment_thesis", "financial_quality", "bottom_line"),
    "rbi_repo_hike": ("investment_thesis", "risk_assessment", "bottom_line"),
    "repo_rate": ("investment_thesis", "financial_quality", "risk_assessment"),
    "quarterly_results": ("financial_quality", "investment_thesis", "bottom_line", "confidence"),
    "earnings_miss": ("financial_quality", "risk_assessment", "bottom_line"),
    "earnings_beat": ("financial_quality", "bull_case", "bottom_line"),
    "ceo_resignation": ("business_quality", "risk_assessment", "bottom_line"),
    "management_change": ("business_quality", "bottom_line"),
    "forecast_revision": ("investment_thesis", "confidence", "bottom_line"),
}


def assess_impact(
    classified: Sequence[ClassifiedChange],
    *,
    current: CompanySnapshot,
    decision_id: str = "",
    graph_meta: Optional[dict[str, Any]] = None,
) -> ImpactAssessment:
    ticker = current.ticker
    entities: list[str] = [ticker]
    reasons: list[str] = []
    decisions: list[str] = []
    forecasts: list[str] = []

    meta = graph_meta or {}
    metric_ids = meta.get("metric_ids") or {}

    for row in classified:
        key = str(row.change.key or "").lower()
        entities.append(f"{row.category}:{key}")
        for reason_key in _REASON_MAP.get(key, ()):
            reasons.append(reason_key)
        if row.category in {"Valuation"} and metric_ids.get("business_quality"):
            entities.append(str(meta.get("valuation_node_id") or "valuation"))
        if row.category == "Macro":
            entities.append(str(meta.get("rbi_node_id") or "rbi_rate"))
            forecasts.append("base")
            forecasts.append("bull")
            forecasts.append("bear")
        if row.category in {"Quarterly Results", "Forecast", "Risk", "Decision"}:
            if decision_id:
                decisions.append(decision_id)
            elif current.decision_id:
                decisions.append(current.decision_id)
            else:
                decisions.append(f"decision:{ticker}")
        if row.category == "Forecast" or row.change.kind == "forecast":
            forecasts.append("forecast_revision")

    # Deduplicate preserve order
    def _uniq(items: List[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        out: list[str] = []
        for i in items:
            if not i or i in seen:
                continue
            seen.add(i)
            out.append(i)
        return tuple(out)

    return ImpactAssessment(
        affected_companies=(ticker,),
        affected_entities=_uniq(entities),
        affected_reasons=_uniq(reasons),
        affected_decisions=_uniq(decisions),
        affected_forecasts=_uniq(forecasts),
        affected_portfolios=(),  # out of scope for IO-01
    )
