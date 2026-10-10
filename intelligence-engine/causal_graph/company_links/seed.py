"""Company-level causal attachments — upstream drivers into named equities."""

from __future__ import annotations

from typing import Any


def _e(source: str, target: str, strength: float, confidence: float, years: int, sign: int = 1, notes: str = "") -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "relation": "company_driver",
        "direction": "directed",
        "direction_sign": sign,
        "strength": strength,
        "confidence": confidence,
        "evidence_years": years,
        "historical_accuracy": min(0.94, confidence - 0.04),
        "current_relevance": 0.88,
        "evidence": [
            {
                "kind": "company_link",
                "span_years": years,
                "note": notes or f"{source} → {target}",
                "source": "causal_graph.company_links",
            }
        ],
        "validated": True,
    }


COMPANY_LINKS: dict[str, dict[str, Any]] = {
    "HDFCBANK": {
        "ticker": "HDFCBANK",
        "sector": "banks",
        "upstream": ["repo_rate", "nim", "roe", "credit_growth", "cost_of_equity", "bank_multiple"],
        "edges": [
            _e("sector_banks", "HDFCBANK", 0.86, 0.92, 15, notes="Private bank leadership beta to sector"),
            _e("bank_multiple", "HDFCBANK", 0.8, 0.9, 12),
            _e("nim", "HDFCBANK", 0.78, 0.9, 12),
            _e("cost_of_equity", "HDFCBANK", 0.65, 0.84, 10, sign=-1),
        ],
    },
    "KOTAKBANK": {
        "ticker": "KOTAKBANK",
        "sector": "banks",
        "upstream": ["repo_rate", "nim", "roe", "bank_multiple"],
        "edges": [
            _e("sector_banks", "KOTAKBANK", 0.8, 0.9, 12),
            _e("bank_multiple", "KOTAKBANK", 0.76, 0.88, 12),
            _e("nim", "KOTAKBANK", 0.74, 0.88, 12),
        ],
    },
    "SBIN": {
        "ticker": "SBIN",
        "sector": "banks",
        "upstream": ["repo_rate", "credit_growth", "nim", "bank_multiple"],
        "edges": [
            _e("sector_banks", "SBIN", 0.78, 0.88, 15),
            _e("credit_growth", "SBIN", 0.72, 0.86, 12),
            _e("bank_multiple", "SBIN", 0.7, 0.85, 12),
        ],
    },
    "TCS": {
        "ticker": "TCS",
        "sector": "it_services",
        "upstream": ["usd", "us_economy", "it_revenue", "it_margins", "it_cash_flow"],
        "edges": [
            _e("sector_it", "TCS", 0.88, 0.93, 15),
            _e("usd", "TCS", 0.76, 0.9, 15),
            _e("it_cash_flow", "TCS", 0.74, 0.88, 12),
            _e("us_economy", "TCS", 0.7, 0.86, 15),
        ],
    },
    "INFY": {
        "ticker": "INFY",
        "sector": "it_services",
        "upstream": ["usd", "us_economy", "it_revenue", "it_margins"],
        "edges": [
            _e("sector_it", "INFY", 0.86, 0.92, 15),
            _e("usd", "INFY", 0.75, 0.9, 15),
            _e("it_margins", "INFY", 0.72, 0.87, 12),
        ],
    },
    "NESTLEIND": {
        "ticker": "NESTLEIND",
        "sector": "fmcg",
        "upstream": ["inr", "imported_inflation", "consumer_spending", "fmcg_margins", "agriculture"],
        "edges": [
            _e("sector_fmcg", "NESTLEIND", 0.84, 0.91, 12),
            _e("fmcg_margins", "NESTLEIND", 0.78, 0.89, 12),
            _e("consumer_spending", "NESTLEIND", 0.7, 0.86, 12),
            _e("imported_inflation", "NESTLEIND", 0.58, 0.8, 12, sign=-1),
        ],
    },
    "HINDUNILVR": {
        "ticker": "HINDUNILVR",
        "sector": "fmcg",
        "upstream": ["inr", "consumer_spending", "fmcg_margins"],
        "edges": [
            _e("sector_fmcg", "HINDUNILVR", 0.86, 0.92, 15),
            _e("fmcg_margins", "HINDUNILVR", 0.76, 0.88, 12),
            _e("consumer_spending", "HINDUNILVR", 0.72, 0.87, 12),
        ],
    },
    "TATASTEEL": {
        "ticker": "TATASTEEL",
        "sector": "metals",
        "upstream": ["china_economy", "steel", "copper", "metal_margins", "metal_earnings"],
        "edges": [
            _e("sector_metals", "TATASTEEL", 0.85, 0.91, 15),
            _e("steel", "TATASTEEL", 0.84, 0.92, 15),
            _e("metal_earnings", "TATASTEEL", 0.8, 0.9, 12),
            _e("china_economy", "TATASTEEL", 0.72, 0.86, 15),
        ],
    },
    "JSWSTEEL": {
        "ticker": "JSWSTEEL",
        "sector": "metals",
        "upstream": ["china_economy", "steel", "metal_margins"],
        "edges": [
            _e("sector_metals", "JSWSTEEL", 0.82, 0.9, 12),
            _e("steel", "JSWSTEEL", 0.83, 0.91, 12),
            _e("metal_margins", "JSWSTEEL", 0.78, 0.88, 12),
        ],
    },
}
