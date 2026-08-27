"""Identify why evidence is insufficient — LEO + CID + SIF + DVC + checklists."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ecp.schema import (
    CID_TO_LEO,
    COMPANY_KNOWLEDGE_FIELDS,
    EARNINGS_FIELDS,
    ECP_VERSION,
    FINANCIAL_FIELDS,
    MARKET_DATA_FIELDS,
    VALUATION_FIELDS,
)


def _present_leo_types(leo_pkg: Dict[str, Any]) -> Set[str]:
    objs = leo_pkg.get("evidence_objects") or []
    types = {str(o.get("evidence_type")) for o in objs if isinstance(o, dict) and o.get("evidence_type")}
    gate = leo_pkg.get("quality_gate") or {}
    for t in gate.get("present_types") or []:
        types.add(str(t))
    plan = leo_pkg.get("evidence_plan") or leo_pkg.get("plan") or {}
    for t in plan.get("present_evidence") or []:
        types.add(str(t))
    return {t for t in types if t}


def _missing_market_fields(dossier: Dict[str, Any], dvc: Dict[str, Any]) -> List[str]:
    md = dossier.get("market_data") or {}
    vf = dvc.get("validated_fields") or dossier.get("validated_fields") or {}
    missing = []
    mapping = {
        "current_price": ("current_price", "last"),
        "market_cap": ("market_cap", "market_cap"),
        "enterprise_value": ("enterprise_value", "enterprise_value"),
        "shares_outstanding": ("shares_outstanding", "shares_outstanding"),
        "fifty_two_week_high": ("fifty_two_week_high", "fifty_two_week_high"),
        "fifty_two_week_low": ("fifty_two_week_low", "fifty_two_week_low"),
        "volume": ("volume", "volume"),
        "liquidity": ("volume", "volume"),  # proxy
        "dividend_yield": ("dividend_yield", "dividend_yield"),
    }
    for field, (md_key, vf_key) in mapping.items():
        has_md = md.get(md_key) not in (None, "", [], {})
        has_vf = isinstance(vf.get(vf_key), dict) and vf[vf_key].get("value") not in (None, "")
        if not (has_md or has_vf):
            missing.append(field)
    return missing


def _missing_valuation_fields(dossier: Dict[str, Any], dvc: Dict[str, Any]) -> List[str]:
    md = dossier.get("market_data") or {}
    multiples = md.get("valuation_multiples") or {}
    val = (dossier.get("valuation") or {}).get("current") or {}
    vf = dvc.get("validated_fields") or dossier.get("validated_fields") or {}
    missing = []
    checks = {
        "trailing_pe": ("trailing_pe", "trailing_pe"),
        "forward_pe": ("forward_pe", "forward_pe"),
        "ev_ebitda": ("ev_ebitda", "ev_ebitda"),
        "price_to_book": ("price_to_book", "price_to_book"),
        "price_to_sales": ("price_to_sales", "price_to_sales"),
        "peg": ("peg", "peg"),
    }
    for field, (m_key, vf_key) in checks.items():
        has = (
            multiples.get(m_key) not in (None, "")
            or val.get(m_key) not in (None, "")
            or (isinstance(vf.get(vf_key), dict) and vf[vf_key].get("value") not in (None, ""))
        )
        if not has:
            missing.append(field)
    if not (dossier.get("valuation") or {}).get("historical"):
        missing.append("historical_valuation")
    if not ((dossier.get("peer_comparison") or {}).get("peers") or (dossier.get("peer_comparison") or {}).get("valuation")):
        missing.append("peer_valuation")
    # DCF optional — only flag if valuation pack has no intrinsic
    if not val.get("dcf") and not (dossier.get("valuation") or {}).get("intrinsic_value"):
        missing.append("dcf")
    return missing


def _missing_financial_fields(dossier: Dict[str, Any]) -> List[str]:
    fs = dossier.get("financial_statements") or {}
    fm = dossier.get("financial_metrics") or {}
    missing = []
    if not (fs.get("income_statement") or {}).get("annual") and not (fs.get("income_statement") or {}).get("quarterly"):
        missing.append("income_statement")
    if not (fs.get("balance_sheet") or {}).get("annual") and not (fs.get("balance_sheet") or {}).get("quarterly"):
        missing.append("balance_sheet")
    if not (fs.get("cash_flow") or {}).get("annual") and not (fs.get("cash_flow") or {}).get("quarterly"):
        missing.append("cash_flow")
    if not dossier.get("quarterly_results") and not (dossier.get("documents") or {}).get("quarterly_results"):
        missing.append("quarterly_results")
    if not dossier.get("annual_reports") and not (dossier.get("documents") or {}).get("annual_reports"):
        missing.append("annual_results")
    for f in (
        "revenue_growth",
        "eps_growth",
        "operating_margin",
        "profit_margin",
        "roe",
        "roce",
        "debt",
        "free_cash_flow",
    ):
        # map aliases
        key = "net_margin" if f == "profit_margin" else ("fcf" if f == "free_cash_flow" else f)
        val = fm.get(key) if key in fm else fm.get(f)
        if val in (None, "", []) or (isinstance(val, str) and val.startswith("Required sector KPI")):
            missing.append(f)
    return missing


def _missing_sector_kpis(dossier: Dict[str, Any], sif_pkg: Dict[str, Any]) -> List[str]:
    priority = list(
        (sif_pkg.get("priority_metrics") or [])
        or ((dossier.get("sector_kpis") or {}).get("priority_metrics") or [])
        or ((dossier.get("sector_framework") or {}).get("priority_metrics") or [])
    )
    if not priority:
        try:
            from sif.frameworks import FRAMEWORKS
            from sif.detection import COMPANY_SECTOR

            sector_id = (
                sif_pkg.get("sector_id")
                or (dossier.get("identity") or {}).get("sector_id")
                or (dossier.get("sector_framework") or {}).get("sector_id")
                or COMPANY_SECTOR.get(str(dossier.get("ticker") or "").upper())
            )
            fw = FRAMEWORKS.get(str(sector_id or ""))
            if fw:
                priority = list(getattr(fw, "priority_metrics", None) or [])
        except Exception:
            priority = []
    fm = dossier.get("financial_metrics") or {}
    sk = (dossier.get("sector_kpis") or {}).get("values") or {}
    missing = []
    for kpi in priority:
        val = sk.get(kpi)
        if val in (None, ""):
            val = fm.get(kpi)
        if val in (None, "", []) or (isinstance(val, str) and val.startswith("Required sector KPI")):
            missing.append(kpi)
    return missing


def _missing_company_knowledge(dossier: Dict[str, Any]) -> List[str]:
    biz = dossier.get("business_profile") or {}
    mgmt = dossier.get("management") or {}
    missing = []
    if not biz.get("business_model"):
        missing.append("business_model")
    if not biz.get("competitive_position"):
        missing.append("competitive_position")
    if not (mgmt.get("ceo") or mgmt.get("cfo")):
        missing.append("management")
    if not (biz.get("products") or biz.get("services")):
        missing.append("products")
    if not biz.get("brands"):
        missing.append("brands")
    if not biz.get("customers"):
        missing.append("customers")
    if not biz.get("suppliers"):
        missing.append("suppliers")
    if not (dossier.get("risks") or dossier.get("key_risks")):
        missing.append("risks")
    if not (dossier.get("catalysts") or dossier.get("key_catalysts")):
        missing.append("catalysts")
    if not (dossier.get("historical_research") or dossier.get("research_history")):
        missing.append("historical_research")
    if not (dossier.get("prediction_history") or dossier.get("predictions")):
        missing.append("prediction_history")
    return missing


def identify_gaps(
    *,
    ticker: str | None,
    leo_pkg: Optional[Dict[str, Any]] = None,
    cid: Optional[Dict[str, Any]] = None,
    sif_pkg: Optional[Dict[str, Any]] = None,
    dvc_pkg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Determine WHY evidence is insufficient — structured gap report."""
    leo_pkg = leo_pkg or {}
    cid = cid or {}
    sif_pkg = sif_pkg or {}
    dvc_pkg = dvc_pkg or {}

    gate = leo_pkg.get("quality_gate") or {}
    leo_missing = list(gate.get("must_have_missing") or gate.get("missing_evidence") or [])
    # Also include plan missing
    plan = leo_pkg.get("evidence_plan") or leo_pkg.get("plan") or {}
    for t in plan.get("missing_evidence") or []:
        if t not in leo_missing:
            leo_missing.append(t)

    cid_missing = list(cid.get("missing_evidence") or [])
    fs = cid.get("financial_statements") or {}
    has_canonical_financials = bool(
        (fs.get("income_statement") or {}).get("annual")
        and (fs.get("balance_sheet") or {}).get("annual")
        and (fs.get("cash_flow") or {}).get("annual")
    )
    if has_canonical_financials:
        leo_missing = [item for item in leo_missing if item != "financial_statements"]
        cid_missing = [item for item in cid_missing if item != "financial_statements"]
    # Map CID categories into LEO-type targets
    for cat in cid_missing:
        leo_t = CID_TO_LEO.get(cat)
        if leo_t and leo_t not in leo_missing:
            leo_missing.append(leo_t)

    market_missing = _missing_market_fields(cid, dvc_pkg)
    valuation_missing = _missing_valuation_fields(cid, dvc_pkg)
    financial_missing = _missing_financial_fields(cid)
    sector_missing = _missing_sector_kpis(cid, sif_pkg)
    knowledge_missing = _missing_company_knowledge(cid)

    # Earnings gaps from LEO types
    present = _present_leo_types(leo_pkg)
    earnings_missing = [f for f in ("earnings_transcript", "broker_consensus") if f not in present]
    if "quarterly_results" not in present:
        earnings_missing.append("latest_results")

    # Target LEO types ECP should attempt to complete
    target_leo_types: List[str] = []
    for t in leo_missing:
        if t not in target_leo_types:
            target_leo_types.append(t)
    if market_missing and "market_data" not in target_leo_types:
        target_leo_types.append("market_data")
    if valuation_missing and "valuation_metrics" not in target_leo_types:
        target_leo_types.append("valuation_metrics")
    if any(f in financial_missing for f in ("income_statement", "balance_sheet", "cash_flow")):
        if "financial_statements" not in target_leo_types:
            target_leo_types.append("financial_statements")
    if sector_missing and "sector_kpis" not in target_leo_types:
        target_leo_types.append("sector_kpis")

    all_item_gaps = {
        "market_data": market_missing,
        "valuation": valuation_missing,
        "financials": financial_missing,
        "earnings": earnings_missing,
        "sector_kpis": sector_missing,
        "company_knowledge": knowledge_missing,
    }
    flat_missing = []
    for fam, items in all_item_gaps.items():
        for item in items:
            flat_missing.append({"family": fam, "item": item})

    blocked = bool(gate.get("blocked")) or bool((sif_pkg.get("recommendation_gate") or {}).get("blocked"))

    return {
        "ecp_version": ECP_VERSION,
        "ticker": (ticker or "").upper() or None,
        "blocked_before": blocked,
        "leo_missing": leo_missing,
        "cid_missing": cid_missing,
        "must_have_missing": [
            item
            for item in (gate.get("must_have_missing") or [])
            if not (has_canonical_financials and item == "financial_statements")
        ],
        "target_leo_types": target_leo_types,
        "item_gaps": all_item_gaps,
        "flat_missing": flat_missing,
        "missing_count": len(flat_missing),
        "present_leo_types": sorted(present),
        "why": _why_message(blocked, leo_missing, flat_missing),
    }


def _why_message(blocked: bool, leo_missing: List[str], flat: List[Dict[str, Any]]) -> str:
    if not blocked and not leo_missing and not flat:
        return "Evidence quality sufficient for gate evaluation."
    parts = []
    if leo_missing:
        parts.append("LEO missing: " + ", ".join(leo_missing[:8]))
    if flat:
        parts.append("Checklist gaps: " + ", ".join(f"{x['item']}" for x in flat[:10]))
    return "; ".join(parts) if parts else "Evidence incomplete."


def coverage_from_gaps(gaps: Dict[str, Any], *, checklist_size: int | None = None) -> float:
    """Rough coverage % = 1 - missing/expected across families."""
    expected = checklist_size or (
        len(MARKET_DATA_FIELDS)
        + len(VALUATION_FIELDS)
        + len(FINANCIAL_FIELDS)
        + len(EARNINGS_FIELDS)
        + 8  # sector KPI average
        + len(COMPANY_KNOWLEDGE_FIELDS)
    )
    missing = int(gaps.get("missing_count") or 0)
    return round(max(0.0, min(1.0, 1.0 - (missing / max(1, expected)))), 4)
