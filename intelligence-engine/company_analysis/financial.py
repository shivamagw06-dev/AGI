"""Step 3 — Financial intelligence from CID / DVC / FIE-like dossier fields (no raw providers)."""

from __future__ import annotations

from typing import Any

from company_analysis.cid_bridge import normalise_financials, normalise_kpi_trends, unwrap_validated
from company_analysis.flags import flag_financial


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _pick(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return None


def _pct_label(v: Any) -> str | None:
    n = _num(v)
    if n is None:
        return None
    # Ratios often arrive as 0.18 or 18
    if abs(n) <= 1.5:
        return f"{n * 100:.1f}%"
    return f"{n:.1f}%"


def analyse_financials(
    *,
    identity: dict[str, Any],
    cid: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not flag_financial():
        return {"enabled": False, "bypassed": True}

    cid = cid or {}
    dvc = dvc_pkg or {}
    validated = unwrap_validated(dvc.get("validated_fields") or cid.get("validated_fields") or {})
    fin = normalise_financials(cid)
    hist = dict(cid.get("financial_history") or {})
    if not hist.get("kpi_trends") and isinstance(cid.get("historical_kpi_trends"), dict):
        hist = {**hist, "kpi_trends": cid.get("historical_kpi_trends")}
    metrics = {**fin, **validated}

    growth = _pick(metrics, "revenue_growth", "sales_growth", "loan_growth", "growth", "earnings_growth")
    margins = _pick(metrics, "operating_margin", "npm", "net_margin", "nim", "ebitda_margin", "gross_margin", "margin")
    returns = _pick(metrics, "roe", "roic", "roa", "return_on_equity")
    cash = _pick(metrics, "fcf", "free_cash_flow", "operating_cash_flow", "cash_conversion")
    leverage = _pick(metrics, "debt_to_equity", "leverage", "cet1", "capital_adequacy", "current_ratio")
    credit = _pick(metrics, "credit_cost", "gnpa", "nnpa", "provision_coverage")
    revenue = _pick(metrics, "revenue", "total_revenue")
    ebitda = _pick(metrics, "ebitda")

    improved: list[str] = []
    deteriorated: list[str] = []
    monitor: list[str] = []

    # Trend hints from history blocks if present (incl. soft KPI trends)
    trends = normalise_kpi_trends(hist)
    for label, key in (
        ("growth", "growth"),
        ("growth", "revenue_growth"),
        ("margins", "margins"),
        ("margins", "operating_margin"),
        ("returns", "returns"),
        ("returns", "roe"),
        ("cash_flow", "cash_flow"),
        ("cash_flow", "fcf"),
        ("asset_quality", "asset_quality"),
    ):
        direction = str((trends.get(key) or "")).lower()
        if direction in {"up", "improving", "better"} and label not in improved:
            improved.append(label)
        elif direction in {"down", "deteriorating", "worse"} and label not in deteriorated:
            deteriorated.append(label)

    sector = str(identity.get("sector_id") or identity.get("sector") or "").lower()
    if "bank" in sector:
        monitor.extend(["NIM trajectory", "Credit cost", "CASA mix", "Loan growth vs deposit growth", "Capital (CET1)"])
        if credit is None:
            deteriorated.append("credit_cost_coverage_missing")
        if returns is not None:
            monitor.append("ROE sustainability vs leverage/credit cost")
    elif "fmcg" in sector or "staple" in sector:
        monitor.extend(["Volume vs pricing", "Gross margin", "Working capital days", "A&P intensity", "ROIC"])
    else:
        monitor.extend(["Revenue growth quality", "Margin durability", "Cash conversion", "Balance-sheet risk"])

    # Evidence from LEO objects (typed, not raw)
    leo_types = []
    for obj in (leo_pkg or {}).get("evidence_objects") or []:
        if isinstance(obj, dict) and obj.get("type"):
            leo_types.append(str(obj.get("type")))

    coverage = 0
    for v in (growth, margins, returns, cash, leverage):
        if v is not None:
            coverage += 20
    if hist:
        coverage = min(100, coverage + 10)
    if validated:
        coverage = min(100, coverage + 10)

    narrative_bits = []
    if returns is not None:
        narrative_bits.append(
            f"Capital returns remain a core quality signal (ROE/ROIC around {_pct_label(returns) or returns}), "
            "and durability of those returns matters more than a single print."
        )
    if margins is not None:
        narrative_bits.append(
            f"Margin structure ({_pct_label(margins) or margins}) informs pricing power and operating leverage — "
            "watch whether expansion is volume-led or cost-led."
        )
    if growth is not None:
        narrative_bits.append(
            f"Growth momentum ({_pct_label(growth) or growth}) should be judged for quality of earnings, not headline rate alone."
        )
    if cash is not None:
        narrative_bits.append(
            "Cash generation capacity supports financial flexibility and capital allocation options through the cycle."
        )
    if ebitda is not None or revenue is not None:
        narrative_bits.append(
            "Scale metrics in the dossier support assessment of earnings power versus balance-sheet claims."
        )
    if improved:
        narrative_bits.append(f"Improving trends noted in: {', '.join(improved)}.")
    if deteriorated:
        narrative_bits.append(f"Areas needing scrutiny: {', '.join(deteriorated)}.")
    if not narrative_bits:
        narrative_bits.append(
            "Financial coverage in the living dossier is incomplete — conclusions are limited to available institutional evidence."
        )

    return {
        "enabled": True,
        "growth": growth,
        "margins": margins,
        "revenue": revenue,
        "ebitda": ebitda,
        "capital_allocation": _pick(metrics, "capital_allocation", "dividend_payout", "buyback", "dividend_yield"),
        "cash_flow": cash,
        "balance_sheet": {
            "leverage": leverage,
            "credit_or_asset_quality": credit,
            "current_ratio": _pick(metrics, "current_ratio"),
        },
        "returns": returns,
        "historical_trends": trends or hist.get("summary") or {},
        "statement_coverage": (hist.get("coverage") or hist.get("counts") or {}),
        "financial_health": "monitored" if coverage >= 40 else "insufficient_coverage",
        "what_improved": improved,
        "what_deteriorated": deteriorated,
        "what_deserves_monitoring": monitor[:8],
        "coverage_pct": coverage,
        "narrative": " ".join(narrative_bits),
        "leo_evidence_types": sorted(set(leo_types))[:12],
        "sources": [
            "cid.financials",
            "cid.financial_metrics",
            "cid.financial_history",
            "dvc.validated_fields",
            "leo.evidence_objects",
        ],
    }
