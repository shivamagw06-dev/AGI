"""Soft-attach DVC validated fields into CID — additive metadata only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from dvc.schema import DVC_VERSION
from dvc.validate import panel_for_company


def merge_dvc_into_dossier(dossier: Dict[str, Any], package: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach DVC audited field metadata to CID.
    Does not overwrite existing institutional values unless DVC has higher confidence
    and the dossier field is empty / missing provenance.
    """
    if not isinstance(dossier, dict) or not isinstance(package, dict):
        return dossier
    if not package.get("enabled", True) and not package.get("validated_fields"):
        return dossier

    now = datetime.now(timezone.utc).isoformat()
    d = dict(dossier)
    fields = dict(package.get("validated_fields") or {})

    # Market data — fill empties from canonical consensus; always attach provenance side-car
    md = dict(d.get("market_data") or {})
    _fill_if_empty(md, "current_price", _val(fields, "last"))
    _fill_if_empty(md, "volume", _val(fields, "volume"))
    _fill_if_empty(md, "market_cap", _val(fields, "market_cap"))
    _fill_if_empty(md, "fifty_two_week_high", _val(fields, "fifty_two_week_high"))
    _fill_if_empty(md, "fifty_two_week_low", _val(fields, "fifty_two_week_low"))
    _fill_if_empty(md, "dividend_yield", _val(fields, "dividend_yield"))
    _fill_if_empty(md, "beta", _val(fields, "beta"))
    _fill_if_empty(md, "enterprise_value", _val(fields, "enterprise_value"))
    multiples = dict(md.get("valuation_multiples") or {})
    for k in ("trailing_pe", "forward_pe", "price_to_book"):
        if _val(fields, k) is not None and multiples.get(k) is None:
            multiples[k] = _val(fields, k)
    if multiples:
        md["valuation_multiples"] = multiples
    md["updated_at"] = md.get("updated_at") or now
    d["market_data"] = md

    # Identity
    ident = dict(d.get("identity") or {})
    _fill_if_empty(ident, "company_name", _val(fields, "company_name"))
    _fill_if_empty(ident, "sector", _val(fields, "sector"))
    _fill_if_empty(ident, "industry", _val(fields, "industry"))
    _fill_if_empty(ident, "market_cap", _val(fields, "market_cap"))
    d["identity"] = ident

    # Financial metrics
    fm = dict(d.get("financial_metrics") or {})
    for src, dest in (
        ("roe", "roe"),
        ("roa", "roa"),
        ("revenue_growth", "revenue_growth"),
        ("operating_margin", "operating_margin"),
        ("profit_margin", "net_margin"),
        ("revenue", "revenue"),
        ("shares_outstanding", "shares_outstanding"),
    ):
        if _val(fields, src) is not None and fm.get(dest) is None:
            fm[dest] = _val(fields, src)
    d["financial_metrics"] = fm

    # Audited field side-car (every stored field with DVC metadata)
    d["validated_fields"] = fields
    d["dvc"] = {
        "dvc_version": DVC_VERSION,
        "attached_at": now,
        "quality": package.get("quality"),
        "grades": package.get("grades"),
        "conflicts": package.get("conflicts") or [],
        "conflict_summary": package.get("conflict_summary"),
        "consensus_history_note": "per-field consensus_history inside validated_fields",
        "winning_provider": package.get("winning_provider_summary"),
        "self_healing": package.get("self_healing"),
        "panel": panel_for_company(package),
    }
    # Surface grades for company page / Ask AGI
    grades = package.get("grades") or {}
    if grades.get("research_grade"):
        d["research_grade"] = grades.get("research_grade")
    if grades.get("data_grade"):
        d["data_grade"] = grades.get("data_grade")
    if grades.get("knowledge_grade"):
        d["knowledge_grade"] = grades.get("knowledge_grade")
    d["data_quality_panel"] = panel_for_company(package)
    d["updated_at"] = now
    return d


def _val(fields: Dict[str, Any], name: str) -> Any:
    vf = fields.get(name)
    if isinstance(vf, dict):
        return vf.get("value")
    return None


def _fill_if_empty(target: Dict[str, Any], key: str, value: Any) -> None:
    if value is None or value == "":
        return
    if target.get(key) in (None, "", [], {}):
        target[key] = value
