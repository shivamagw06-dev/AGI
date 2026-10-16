"""Evidence requirements — what must be acquired for the research objective."""

from __future__ import annotations

from typing import Any

from acquisition_planner.schema import IAPE_CONSTITUTION

EVIDENCE_CATALOG: dict[str, dict[str, Any]] = {
    "official_filings": {
        "label": "Official Filings",
        "preferred_providers": ["company_ir", "nse", "bse", "sec_edgar", "fil"],
        "data_types": ["annual_report", "quarterly_report", "filings"],
        "min_tier": 1,
    },
    "quarterly_results": {
        "label": "Quarterly Results",
        "preferred_providers": ["company_ir", "nse", "bse", "fil"],
        "data_types": ["quarterly_report", "earnings"],
        "min_tier": 1,
    },
    "historical_financials": {
        "label": "Historical Financials",
        "preferred_providers": ["fmp", "groww", "yahoo_finance", "fil"],
        "data_types": ["fundamentals", "financials"],
        "min_tier": 2,
    },
    "peer_metrics": {
        "label": "Peer Metrics",
        "preferred_providers": ["pil", "fmp", "groww", "yahoo_finance"],
        "data_types": ["peer_metrics", "fundamentals"],
        "min_tier": 2,
    },
    "macro_data": {
        "label": "Macro Data",
        "preferred_providers": ["fred", "rbi", "world_bank", "imf"],
        "data_types": ["macro", "rates", "policy"],
        "min_tier": 1,
    },
    "management_commentary": {
        "label": "Management Commentary",
        "preferred_providers": ["conference_calls", "investor_presentations", "company_ir"],
        "data_types": ["transcript", "guidance", "presentation"],
        "min_tier": 1,
    },
    "historical_valuation": {
        "label": "Historical Valuation",
        "preferred_providers": ["groww", "indianapi", "yahoo_finance", "fmp"],
        "data_types": ["valuation", "pe", "price"],
        "min_tier": 2,
    },
    "portfolio_exposure": {
        "label": "Portfolio Exposure",
        "preferred_providers": ["ilm", "ikg", "pil"],
        "data_types": ["portfolio", "exposure", "memory"],
        "min_tier": 3,
    },
    "live_prices": {
        "label": "Live / Market Prices",
        "preferred_providers": ["groww", "indianapi", "yahoo_finance", "polygon", "finnhub"],
        "data_types": ["price", "ohlc", "volume"],
        "min_tier": 2,
    },
    "regulatory_policy": {
        "label": "Regulatory / Policy",
        "preferred_providers": ["sebi", "rbi", "sec_edgar"],
        "data_types": ["regulation", "policy"],
        "min_tier": 1,
    },
    "press_flow": {
        "label": "Press / News Flow",
        "preferred_providers": ["press_releases", "company_ir", "eil", "tavily", "exa"],
        "data_types": ["press", "news"],
        "min_tier": 1,
    },
    "knowledge_graph_context": {
        "label": "Knowledge Graph Context",
        "preferred_providers": ["ikg", "ilm", "fil"],
        "data_types": ["graph", "memory"],
        "min_tier": 3,
    },
    "evidence_corpus": {
        "label": "Evidence Corpus",
        "preferred_providers": ["eil", "fil", "ilm", "exa", "firecrawl"],
        "data_types": ["evidence", "citations", "research"],
        "min_tier": 3,
    },
    "web_research": {
        "label": "Web Research Context",
        "preferred_providers": ["exa", "firecrawl", "playwright", "tavily", "browserbase"],
        "data_types": ["research", "industry_report", "web", "markdown"],
        "min_tier": 3,
    },
}


def _needs_from_objective(objective_type: str, intent_family: str) -> list[str]:
    mapping: dict[str, list[str]] = {
        "valuation_assessment": ["historical_valuation", "historical_financials", "peer_metrics", "official_filings"],
        "risk_assessment": ["official_filings", "quarterly_results", "macro_data", "regulatory_policy", "portfolio_exposure"],
        "opportunity_assessment": ["historical_valuation", "peer_metrics", "management_commentary", "quarterly_results"],
        "comparison_assessment": ["peer_metrics", "historical_financials", "historical_valuation", "knowledge_graph_context"],
        "forecast_assessment": ["historical_financials", "macro_data", "management_commentary", "quarterly_results"],
        "portfolio_assessment": ["portfolio_exposure", "live_prices", "peer_metrics", "risk_assessment"],
        "educational_explanation": ["knowledge_graph_context", "evidence_corpus"],
        "fact_retrieval": ["live_prices", "evidence_corpus", "knowledge_graph_context"],
        "decision_support": [
            "official_filings",
            "quarterly_results",
            "historical_financials",
            "peer_metrics",
            "macro_data",
            "management_commentary",
            "historical_valuation",
            "portfolio_exposure",
            "web_research",
        ],
        "monitoring_update": ["live_prices", "press_flow", "quarterly_results", "evidence_corpus", "web_research"],
    }
    keys = list(mapping.get(objective_type, mapping["decision_support"]))
    if intent_family == "portfolio":
        if "portfolio_exposure" not in keys:
            keys.insert(0, "portfolio_exposure")
    if intent_family == "macro":
        if "macro_data" not in keys:
            keys.insert(0, "macro_data")
    if intent_family == "educational":
        keys = ["knowledge_graph_context", "evidence_corpus"]
    # fix portfolio_assessment recursive typo
    keys = [k for k in keys if k != "risk_assessment"]
    if objective_type == "portfolio_assessment" and "macro_data" not in keys:
        keys.append("macro_data")
    return keys


def derive_evidence_requirements(
    *,
    research_question: str,
    primary_objective: str | None = None,
    intent_family: str | None = None,
    required_layers: list[str] | None = None,
) -> dict[str, Any]:
    obj = (primary_objective or "decision_support").strip().lower()
    family = (intent_family or "company").strip().lower()
    keys = _needs_from_objective(obj, family)
    layer_boost = {
        "FIL": "official_filings",
        "PIL": "peer_metrics",
        "EIL": "evidence_corpus",
        "ILM": "knowledge_graph_context",
        "IKG": "knowledge_graph_context",
        "MDI": "macro_data",
        "QIL": "live_prices",
        "RIL": "regulatory_policy",
        "MIL": "management_commentary",
    }
    for layer in required_layers or []:
        code = str(layer).upper()
        need = layer_boost.get(code)
        if need and need not in keys:
            keys.append(need)

    required = []
    for key in keys:
        cat = EVIDENCE_CATALOG.get(key)
        if not cat:
            continue
        required.append(
            {
                "evidence_key": key,
                "label": cat["label"],
                "preferred_providers": list(cat["preferred_providers"]),
                "data_types": list(cat["data_types"]),
                "min_tier": cat["min_tier"],
                "research_purpose": f"Required to answer: {research_question[:120]}",
            }
        )
    return {
        "research_question": research_question,
        "primary_objective": obj,
        "intent_family": family,
        "required_data": required,
        "required_count": len(required),
        "constitution_id": IAPE_CONSTITUTION["id"],
    }
