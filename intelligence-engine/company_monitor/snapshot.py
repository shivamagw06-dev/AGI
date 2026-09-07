"""Build a monitorable snapshot from institutional layers only (no raw providers)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _pick(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, "", []):
            return d[k]
    return None


def build_snapshot(
    ticker: str,
    *,
    cid: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    financial: dict[str, Any] | None = None,
    valuation: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    house_view: dict[str, Any] | None = None,
    predictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    t = (ticker or "").upper()
    cid = cid or {}
    leo = leo_pkg or {}
    fin_src = financial or cid.get("financials") or cid.get("financial_intelligence") or {}
    val_src = valuation or cid.get("valuation") or {}
    validated = cid.get("validated_fields") or {}

    metrics = {
        "revenue_growth": _num(_pick(fin_src, "revenue_growth", "sales_growth", "growth") or validated.get("revenue_growth")),
        "operating_margin": _num(_pick(fin_src, "operating_margin", "ebitda_margin", "margin", "nim") or validated.get("operating_margin")),
        "roe": _num(_pick(fin_src, "roe", "returns", "return_on_equity") or validated.get("roe")),
        "debt": _num(_pick(fin_src, "debt", "net_debt", "leverage", "debt_to_equity") or validated.get("debt")),
        "cash_flow": _num(_pick(fin_src, "fcf", "operating_cash_flow", "cash_flow", "cash_conversion") or validated.get("fcf")),
        "pe": _num(_pick(val_src, "pe", "current_pe") or validated.get("pe")),
        "historical_pe": _num(_pick(val_src, "historical_pe", "pe_median", "avg_pe")),
        "pb": _num(_pick(val_src, "pb") or validated.get("pb")),
    }

    # Nested financial_intelligence from Company Analysis
    if isinstance(financial, dict) and financial.get("returns") is not None and metrics["roe"] is None:
        metrics["roe"] = _num(financial.get("returns"))
    if isinstance(valuation, dict):
        if metrics["pe"] is None:
            metrics["pe"] = _num(valuation.get("current_pe") or valuation.get("pe"))
        if metrics["historical_pe"] is None:
            metrics["historical_pe"] = _num(valuation.get("historical_pe"))

    identity = cid.get("identity") or {}
    evidence_types = []
    for obj in leo.get("evidence_objects") or []:
        if isinstance(obj, dict) and obj.get("type"):
            evidence_types.append(str(obj["type"]))

    hv = house_view or {}
    hv_label = hv.get("current_view") or hv.get("stance") or hv.get("label") or hv.get("house_view")

    return {
        "ticker": t,
        "company_name": identity.get("company_name") or t,
        "sector_id": identity.get("sector_id") or (cid.get("sector_framework") or {}).get("sector_id"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "coverage_score": cid.get("coverage_score"),
        "coverage_grade": cid.get("coverage_grade"),
        "leo_evidence_count": len(leo.get("evidence_objects") or []),
        "leo_evidence_types": sorted(set(evidence_types))[:20],
        "house_view_label": hv_label,
        "prediction_count": len(predictions or []),
        "business_quality_score": ((company_analysis or {}).get("business_quality") or {}).get(
            "business_quality_score"
        ),
        "channels_seen": {
            "financial_statements": bool(fin_src or validated),
            "price": metrics.get("pe") is not None or metrics.get("pb") is not None,
            "news": "news" in evidence_types or "headline" in evidence_types,
            "quarterly_results": "earnings" in " ".join(evidence_types).lower()
            or "results" in " ".join(evidence_types).lower(),
            "house_view": bool(hv_label),
            "predictions": bool(predictions),
            "corporate_actions": any(
                x in " ".join(evidence_types).lower() for x in ("dividend", "buyback", "split", "bonus")
            ),
            "management_changes": "management" in " ".join(evidence_types).lower(),
            "ratings": "rating" in " ".join(evidence_types).lower(),
        },
        "knowledge_age_hint": cid.get("updated_at") or cid.get("last_updated"),
    }
