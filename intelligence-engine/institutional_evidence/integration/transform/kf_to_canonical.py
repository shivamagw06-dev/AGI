"""Knowledge Transformation — KF / CGL extracts → canonical domain models.

Provider schemas never reach downstream engines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...canonical.domains import empty_domain_bundle
from ...canonical.statements import map_provider_to_canonical
from ...entity.resolve import entity_id_for_ticker, resolve_entity


def _hd_financials_to_periods(ticker: str) -> Dict[str, Any]:
    """Soft-read Knowledge Factory Historical Depth series into period rows."""
    annuals: List[Dict[str, Any]] = []
    quarters: List[Dict[str, Any]] = []
    try:
        from knowledge_factory.historical_depth import store as hd_store

        e = ticker.upper()
        for series_key, bucket, ptype in (
            ("financials_annual", annuals, "annual"),
            ("financials_quarterly", quarters, "quarterly"),
        ):
            series = hd_store.get_series(series_key, e) or {}
            for r in series.get("records") or []:
                if not isinstance(r, dict):
                    continue
                payload = r.get("payload") if isinstance(r.get("payload"), dict) else r
                row = {
                    "period": r.get("period")
                    or payload.get("period")
                    or r.get("period_end")
                    or payload.get("period_end")
                    or "unknown",
                    "period_end": r.get("period_end") or payload.get("period_end"),
                    "period_type": ptype,
                    "revenue": payload.get("revenue") or payload.get("total_income"),
                    "ebitda": payload.get("ebitda"),
                    "pat": payload.get("pat")
                    or payload.get("net_income")
                    or payload.get("net_profit"),
                    "eps": payload.get("eps"),
                    "total_debt": payload.get("total_debt") or payload.get("debt"),
                    "cash": payload.get("cash") or payload.get("cash_and_equivalents"),
                    "capex": payload.get("capex"),
                    "evidence_refs": [f"kf_hd:{series_key}:{e}"],
                }
                bucket.append(row)
    except Exception:
        pass
    return {"annual_history": annuals, "quarter_history": quarters}


def _cgl_extract(ticker: str) -> Dict[str, Any]:
    try:
        from continuous_gather_learn import persist as cgl_persist

        return cgl_persist.get_knowledge_extract(ticker.upper()) or {}
    except Exception:
        return {}


def _corporate_actions(ticker: str) -> List[Dict[str, Any]]:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        series = hd_store.get_series("corporate_actions", ticker.upper()) or {}
        out = []
        for r in series.get("records") or []:
            if isinstance(r, dict):
                p = r.get("payload") if isinstance(r.get("payload"), dict) else r
                out.append(p)
        return out
    except Exception:
        return []


def transform_company_knowledge(ticker: str) -> Dict[str, Any]:
    """Transform gathered knowledge into canonical models for one company."""
    resolved = resolve_entity(ticker)
    if not resolved.get("resolved"):
        # Still allow ticker-shaped input for Phase-1 tickers
        t = str(ticker or "").upper().strip()
        eid = entity_id_for_ticker(t)
        company = t
    else:
        t = resolved["ticker"]
        eid = resolved["entity_id"]
        company = str(resolved.get("company") or t)

    bundle = empty_domain_bundle(eid, t, name=company)
    hd = _hd_financials_to_periods(t)
    extract = _cgl_extract(t)

    # Merge extract metrics as soft ratios on latest period scaffold
    if extract.get("metrics") and not (hd.get("annual_history") or hd.get("quarter_history")):
        # No periods — keep financials unpublished; metrics go to valuation/forecast soft fields
        pass

    canon = map_provider_to_canonical(
        {
            **hd,
            "published": bool(hd.get("annual_history") or hd.get("quarter_history")),
            "source": "knowledge_factory_historical_depth",
        },
        company=company,
        ticker=t,
        source="knowledge_integration_layer",
    )
    fin = canon.to_dict()
    bundle["models"]["CanonicalFinancialStatements"] = fin
    bundle["models"]["CanonicalCompany"] = {
        **bundle["models"]["CanonicalCompany"],
        "name": company,
        "sector": (resolved or {}).get("sector") or "",
        "aliases": (resolved or {}).get("aliases") or [],
    }

    actions = _corporate_actions(t)
    bundle["models"]["CanonicalCorporateActions"] = {
        **bundle["models"]["CanonicalCorporateActions"],
        "actions": actions,
        "evidence_refs": [f"kf_hd:corporate_actions:{t}"] if actions else [],
    }

    # Soft company intelligence
    try:
        from knowledge_factory.company_intelligence.production import get_company

        ci = get_company(t)
        if isinstance(ci, dict):
            bundle["models"]["CanonicalCompany"]["sector"] = (
                bundle["models"]["CanonicalCompany"].get("sector")
                or ci.get("sector")
                or ""
            )
            if ci.get("isin"):
                bundle["models"]["CanonicalCompany"]["isin"] = ci.get("isin")
    except Exception:
        pass

    metrics = (extract or {}).get("metrics") or {}
    if metrics:
        bundle["models"]["CanonicalValuation"] = {
            **bundle["models"]["CanonicalValuation"],
            "multiples": {k: metrics[k] for k in metrics if "margin" in k or "roe" in k or "roce" in k},
            "evidence_refs": ["cgl:knowledge_extract"],
        }
        bundle["models"]["CanonicalForecast"] = {
            **bundle["models"]["CanonicalForecast"],
            "scenarios": {
                "themes": extract.get("themes") or [],
                "risks": extract.get("risks") or [],
                "catalysts": extract.get("catalysts") or [],
                "metrics": metrics,
            },
            "evidence_refs": ["cgl:knowledge_extract"],
        }

    return {
        "ok": True,
        "entity_id": eid,
        "ticker": t,
        "company": company,
        "models": bundle["models"],
        "financials_published": bool(fin.get("published")),
        "period_count": fin.get("period_count") or 0,
        "corporate_actions_count": len(actions),
        "cgl_extract_present": bool(extract),
        "rule": "Provider schemas never reach downstream engines",
        "source": "kil_transform",
    }
