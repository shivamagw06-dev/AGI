"""FIRE-02 orchestration — load series, run detectors, build driver pack."""

from __future__ import annotations

from typing import Any

from financial_intelligence.confidence import confidence_distribution
from financial_intelligence.drivers.analysis import analyse_all
from financial_intelligence.drivers.schema import (
    DRIVER_METRICS,
    DRIVER_SECTION,
    DRIVER_SUBSECTIONS,
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
    VERSION,
    WORKSTREAM_ID,
)
from financial_intelligence.inventory import load_metric_series

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _coverage_pct(coverage: dict[str, Any]) -> float | None:
    if not coverage:
        return None
    for key in ("overall_completeness_pct", "coverage_pct", "average_coverage_pct"):
        if isinstance(coverage.get(key), (int, float)):
            return float(coverage[key])
    cov = coverage.get("coverage") or {}
    if isinstance(cov.get("coverage_pct"), (int, float)):
        return float(cov["coverage_pct"])
    return None


def _subsection_for(category: str) -> str:
    c = (category or "").lower()
    if "revenue" in c:
        return "revenue_drivers"
    if "margin" in c or "profitability" in c:
        return "margin_drivers" if "margin" in c else "profitability_drivers"
    if "cash" in c:
        return "cash_flow_drivers"
    if "working" in c:
        return "working_capital_drivers"
    if "balance" in c:
        return "balance_sheet_drivers"
    if "capital allocation" in c:
        return "capital_allocation_drivers"
    if "return" in c:
        return "return_drivers"
    return "financial_relationships_summary"


# Map profitability into margin_drivers subsection for report layout per spec
_SUBSECTION_ALIAS = {
    "profitability_drivers": "margin_drivers",
}


def build_driver_pack(
    ticker: str,
    *,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    t = ticker.upper().strip()
    if series_map is not None:
        inv = {"ticker": t, "series": series_map, "coverage": {}, "warehouse_version": None, "notes": []}
    else:
        inv = load_metric_series(t, metrics=DRIVER_METRICS)

    cov_pct = _coverage_pct(inv.get("coverage") or {})
    relationships = analyse_all(inv.get("series") or {}, coverage_pct=cov_pct)
    # Anti-hallucination: drop anything without evidence
    relationships = [r for r in relationships if r.get("evidence")]

    subsections: dict[str, Any] = {k: {"section": k, "findings": [], "prose": None, "n": 0} for k in DRIVER_SUBSECTIONS}
    for r in relationships:
        sub = _SUBSECTION_ALIAS.get(_subsection_for(str(r.get("category"))), _subsection_for(str(r.get("category"))))
        if sub not in subsections:
            sub = "financial_relationships_summary"
        subsections[sub]["findings"].append(r)
    for k, block in subsections.items():
        narrs = [f.get("narrative") or f.get("observation") for f in block["findings"] if f.get("narrative") or f.get("observation")]
        block["n"] = len(block["findings"])
        block["prose"] = " ".join(narrs) if narrs else None

    subsections["financial_relationships_summary"] = {
        "section": "financial_relationships_summary",
        "findings": relationships,
        "n": len(relationships),
        "prose": (
            f"{len(relationships)} evidence-backed financial relationship(s) identified. "
            "No recommendation is issued."
            if relationships
            else "Insufficient aligned warehouse history for cross-statement relationships."
        ),
    }

    dist = confidence_distribution(relationships)
    warnings = [r for r in relationships if str(r.get("severity")) in {"Medium", "High"}]
    cash_warn = [r for r in relationships if "Cash" in str(r.get("category")) and str(r.get("severity")) in {"Medium", "High"}]
    wc_warn = [r for r in relationships if "Working" in str(r.get("category")) and str(r.get("severity")) in {"Medium", "High"}]
    cap_obs = [r for r in relationships if "Capital Allocation" in str(r.get("category"))]
    high_sev = [r for r in relationships if str(r.get("severity")) == "High"]
    by_cat: dict[str, int] = {}
    for r in relationships:
        cat = str(r.get("category") or "Other")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "programme": PROGRAMME,
        "version": VERSION,
        "ticker": t,
        "section": DRIVER_SECTION,
        "title": "Financial Drivers",
        "subsections": subsections,
        "relationships": relationships,
        "n_relationships": len(relationships),
        "driver_categories": by_cat,
        "cash_quality_warnings": cash_warn,
        "working_capital_warnings": wc_warn,
        "capital_allocation_observations": cap_obs,
        "high_severity_findings": high_sev,
        "warnings": warnings,
        "confidence": {"distribution": dist},
        "evidence": {
            "warehouse_version": inv.get("warehouse_version"),
            "coverage_pct": cov_pct,
            "metrics_present": sorted(k for k, v in (inv.get("series") or {}).items() if v),
        },
        "mission_control": {
            "relationship_findings": len(relationships),
            "driver_categories": by_cat,
            "cash_quality_warnings": len(cash_warn),
            "working_capital_warnings": len(wc_warn),
            "capital_allocation_observations": len(cap_obs),
            "high_severity_findings": len(high_sev),
            "confidence_distribution": dist,
        },
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "mutated_warehouse": False,
        "fire_01_unchanged": True,
        "spec": SPEC,
        "as_of": now_iso(),
        "inventory_notes": inv.get("notes") or [],
    }
