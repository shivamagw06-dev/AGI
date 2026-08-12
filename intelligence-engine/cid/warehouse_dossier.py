"""Fast dossier hydration directly from the institutional warehouse."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cid.coverage import compute_coverage
from cid.schema import empty_dossier

TABLE_LIMITS = {
    "company_master": 1,
    "profile_history": 20,
    "peer_relationships": 100,
    "financials_annual": 80,
    "financials_quarterly": 80,
    "historical_ratios": 40,
    "historical_valuation": 120,
    "consensus": 40,
    "ownership": 40,
    "company_intelligence": 10,
    "research_intelligence": 20,
    "research_timeline": 100,
    "corporate_actions": 60,
}


def _rows(table: str, ticker: str, limit: int) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    return list(store.all_rows(table, entity=ticker, limit=limit) or [])


def build(ticker: str) -> dict[str, Any]:
    """Build an OpenAI-ready factual dossier without live provider calls."""
    t = str(ticker or "").strip().upper()
    dossier = empty_dossier(t)
    evidence: dict[str, list[dict[str, Any]]] = {}
    for table, limit in TABLE_LIMITS.items():
        evidence[table] = _rows(table, t, limit)

    master = (evidence.get("company_master") or [{}])[0]
    dossier["identity"].update(
        {
            "company_name": master.get("company_name") or t,
            "legal_name": master.get("legal_name"),
            "nse_symbol": t,
            "bse_code": master.get("bse_symbol"),
            "isin": master.get("isin"),
            "sector": master.get("sector"),
            "industry": master.get("industry"),
            "sub_sector": master.get("sub_industry"),
            "market_cap": master.get("market_cap_inr"),
        }
    )
    dossier["business_profile"].update(
        {
            "business_model": master.get("business_description"),
            "website": master.get("website"),
            "business_type": master.get("business_type"),
            "industry_dna": master.get("industry_dna"),
        }
    )

    annual = evidence.get("financials_annual") or []
    quarterly = evidence.get("financials_quarterly") or []
    ratios = evidence.get("historical_ratios") or []
    valuations = evidence.get("historical_valuation") or []
    peers = evidence.get("peer_relationships") or []
    ownership = evidence.get("ownership") or []
    dossier["financial_statements"]["warehouse_annual"] = annual
    dossier["financial_statements"]["warehouse_quarterly"] = quarterly
    dossier["financial_metrics"] = {
        "latest": ratios[-1] if ratios else {},
        "historical_ratios": ratios,
    }
    dossier["valuation"] = {
        **dossier["valuation"],
        "current": valuations[-1] if valuations else {},
        "historical": valuations,
        "consensus_history": evidence.get("consensus") or [],
    }
    dossier["ownership"] = {
        "current": ownership[-1] if ownership else {},
        "history": ownership,
    }
    dossier["peer_comparison"] = {
        **dossier["peer_comparison"],
        "peer_group": [row.get("peer_symbol") for row in peers if row.get("peer_symbol")],
        "relationships": peers,
    }
    dossier["warehouse_evidence"] = evidence
    dossier["evidence_timeline"] = evidence.get("research_timeline") or []
    dossier["announcements"] = evidence.get("corporate_actions") or []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    dossier["created_at"] = now
    dossier["updated_at"] = now
    dossier["source_policy"] = "institutional_warehouse_only_background_generation"
    cov = compute_coverage(dossier)
    dossier.update(cov)
    return dossier
