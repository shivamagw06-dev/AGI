"""In-memory institutional causal graph — seed relationships with evidence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from causal_graph.company_links.seed import COMPANY_LINKS
from causal_graph.macro_links.seed import MACRO_EDGES, MACRO_NODES
from causal_graph.sector_links.models import SECTOR_MODELS

# Core institutional nodes (economies → companies → multiples)
_BASE_NODES: list[dict[str, Any]] = [
    {"id": "india_economy", "label": "India Economy", "type": "economy", "region": "IN"},
    {"id": "china_economy", "label": "China Economy", "type": "economy", "region": "CN"},
    {"id": "us_economy", "label": "US Economy", "type": "economy", "region": "US"},
    {"id": "india", "label": "India", "type": "country", "region": "IN"},
    {"id": "rbi", "label": "Reserve Bank of India", "type": "central_bank", "region": "IN"},
    {"id": "fed", "label": "US Federal Reserve", "type": "central_bank", "region": "US"},
    {"id": "repo_rate", "label": "RBI Repo Rate", "type": "interest_rate", "region": "IN"},
    {"id": "us_fed_funds", "label": "US Fed Funds", "type": "interest_rate", "region": "US"},
    {"id": "india_10y", "label": "India 10Y Yield", "type": "bond_yield", "region": "IN"},
    {"id": "us_10y", "label": "US 10Y Yield", "type": "bond_yield", "region": "US"},
    {"id": "india_cpi", "label": "India CPI Inflation", "type": "inflation", "region": "IN"},
    {"id": "imported_inflation", "label": "Imported Inflation", "type": "inflation", "region": "IN"},
    {"id": "inr", "label": "INR (Rupee)", "type": "currency", "region": "IN"},
    {"id": "usd", "label": "USD", "type": "currency", "region": "US"},
    {"id": "oil", "label": "Crude Oil", "type": "commodity", "family": "energy"},
    {"id": "gas", "label": "Natural Gas", "type": "commodity", "family": "energy"},
    {"id": "copper", "label": "Copper", "type": "commodity", "family": "metals"},
    {"id": "steel", "label": "Steel", "type": "commodity", "family": "metals"},
    {"id": "coal", "label": "Coal", "type": "commodity", "family": "energy"},
    {"id": "agriculture", "label": "Agriculture Basket", "type": "commodity", "family": "agri"},
    {"id": "sector_banks", "label": "Banks", "type": "sector"},
    {"id": "sector_nbfc", "label": "NBFCs", "type": "sector"},
    {"id": "sector_it", "label": "IT Services", "type": "sector"},
    {"id": "sector_metals", "label": "Metals", "type": "sector"},
    {"id": "sector_fmcg", "label": "FMCG", "type": "sector"},
    {"id": "sector_housing", "label": "Housing", "type": "sector"},
    {"id": "sector_cement", "label": "Cement", "type": "sector"},
    {"id": "sector_capital_goods", "label": "Capital Goods", "type": "sector"},
    {"id": "sector_consumer_internet", "label": "Consumer Internet", "type": "sector"},
    {"id": "nim", "label": "Net Interest Margin", "type": "financial_metric"},
    {"id": "roe", "label": "Return on Equity", "type": "financial_metric"},
    {"id": "credit_growth", "label": "Credit Growth", "type": "financial_metric"},
    {"id": "it_revenue", "label": "IT USD Revenue", "type": "financial_metric"},
    {"id": "it_margins", "label": "IT Operating Margins", "type": "financial_metric"},
    {"id": "it_cash_flow", "label": "IT Free Cash Flow", "type": "financial_metric"},
    {"id": "metal_margins", "label": "Metals Margins", "type": "financial_metric"},
    {"id": "metal_earnings", "label": "Metals Earnings", "type": "financial_metric"},
    {"id": "fmcg_margins", "label": "FMCG Margins", "type": "financial_metric"},
    {"id": "consumer_spending", "label": "Consumer Spending", "type": "financial_metric"},
    {"id": "cost_of_equity", "label": "Cost of Equity", "type": "financial_metric"},
    {"id": "demand", "label": "End Demand", "type": "financial_metric"},
    {"id": "orders", "label": "Order Growth", "type": "financial_metric"},
    {"id": "contribution_margin", "label": "Contribution Margin", "type": "financial_metric"},
    {"id": "fcf", "label": "Free Cash Flow", "type": "financial_metric"},
    {"id": "bank_multiple", "label": "Bank Valuation Multiple", "type": "valuation_multiple"},
    {"id": "it_multiple", "label": "IT Valuation Multiple", "type": "valuation_multiple"},
    {"id": "fmcg_multiple", "label": "FMCG Valuation Multiple", "type": "valuation_multiple"},
    {"id": "systemic_risk", "label": "Systemic Risk", "type": "risk_factor"},
]

_COMPANY_NODES = [
    {"id": "HDFCBANK", "label": "HDFC Bank", "type": "company", "sector": "banks", "ticker": "HDFCBANK"},
    {"id": "KOTAKBANK", "label": "Kotak Mahindra Bank", "type": "company", "sector": "banks", "ticker": "KOTAKBANK"},
    {"id": "SBIN", "label": "State Bank of India", "type": "company", "sector": "banks", "ticker": "SBIN"},
    {"id": "TCS", "label": "Tata Consultancy Services", "type": "company", "sector": "it_services", "ticker": "TCS"},
    {"id": "INFY", "label": "Infosys", "type": "company", "sector": "it_services", "ticker": "INFY"},
    {"id": "NESTLEIND", "label": "Nestlé India", "type": "company", "sector": "fmcg", "ticker": "NESTLEIND"},
    {"id": "HINDUNILVR", "label": "Hindustan Unilever", "type": "company", "sector": "fmcg", "ticker": "HINDUNILVR"},
    {"id": "TATASTEEL", "label": "Tata Steel", "type": "company", "sector": "metals", "ticker": "TATASTEEL"},
    {"id": "JSWSTEEL", "label": "JSW Steel", "type": "company", "sector": "metals", "ticker": "JSWSTEEL"},
]


def _index(items: list[dict[str, Any]], key: str = "id") -> dict[str, dict[str, Any]]:
    return {str(i[key]): i for i in items if i.get(key)}


def nodes() -> list[dict[str, Any]]:
    out = list(MACRO_NODES) + list(_BASE_NODES) + list(_COMPANY_NODES)
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for n in out:
        nid = str(n["id"])
        if nid in seen:
            continue
        seen.add(nid)
        uniq.append(deepcopy(n))
    return uniq


def edges() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out.extend(deepcopy(MACRO_EDGES))
    # Sector model edges
    for model in SECTOR_MODELS.values():
        for e in model.get("edges") or []:
            out.append(deepcopy(e))
    # Company link edges
    for ticker, links in COMPANY_LINKS.items():
        for e in links.get("edges") or []:
            row = deepcopy(e)
            row.setdefault("company", ticker)
            out.append(row)
    # Deduplicate by (source, target, relation)
    seen: set[tuple[str, str, str]] = set()
    uniq: list[dict[str, Any]] = []
    for e in out:
        key = (str(e.get("source")), str(e.get("target")), str(e.get("relation") or "influences"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    return uniq


def node_for(node_id: str) -> dict[str, Any] | None:
    return _index(nodes()).get(str(node_id))


def company_node(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    return node_for(t)


def resolve_company(ticker: str) -> str | None:
    n = company_node(ticker)
    return str(n["id"]) if n else None


def graph_snapshot() -> dict[str, Any]:
    n = nodes()
    e = edges()
    return {
        "node_count": len(n),
        "edge_count": len(e),
        "nodes": n,
        "edges": e,
        "sectors_modelled": list(SECTOR_MODELS.keys()),
        "companies_linked": list(COMPANY_LINKS.keys()),
    }


def outgoing(node_id: str) -> list[dict[str, Any]]:
    nid = str(node_id)
    return [e for e in edges() if str(e.get("source")) == nid]


def incoming(node_id: str) -> list[dict[str, Any]]:
    nid = str(node_id)
    return [e for e in edges() if str(e.get("target")) == nid]
