"""Sector transmission models — banks, IT, metals, consumer internet, FMCG."""

from __future__ import annotations

from typing import Any


def _e(source: str, target: str, strength: float, confidence: float, years: int, sign: int = 1, notes: str = "") -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "relation": "sector_transmission",
        "direction": "directed",
        "direction_sign": sign,
        "strength": strength,
        "confidence": confidence,
        "evidence_years": years,
        "historical_accuracy": min(0.95, confidence - 0.05),
        "current_relevance": 0.86,
        "evidence": [
            {
                "kind": "sector_model",
                "span_years": years,
                "note": notes or f"{source} → {target}",
                "source": "causal_graph.sector_links",
            }
        ],
        "validated": True,
    }


SECTOR_MODELS: dict[str, dict[str, Any]] = {
    "banks": {
        "sector": "banks",
        "chain": ["repo_rate", "nim", "roe", "bank_multiple", "sector_banks"],
        "narrative": "Rates → NIM → ROE → Valuation",
        "edges": [
            _e("repo_rate", "sector_banks", 0.7, 0.88, 14, notes="Policy rate cycle maps to bank earnings power"),
            _e("nim", "sector_banks", 0.78, 0.9, 14),
            _e("credit_growth", "sector_nbfc", 0.72, 0.86, 12),
            _e("sector_banks", "sector_nbfc", 0.6, 0.8, 12),
        ],
    },
    "it_services": {
        "sector": "it_services",
        "chain": ["usd", "it_revenue", "it_margins", "it_cash_flow", "it_multiple", "sector_it"],
        "narrative": "USD → Revenue → Margins → Cash Flow",
        "edges": [
            _e("usd", "sector_it", 0.74, 0.89, 15),
            _e("it_cash_flow", "sector_it", 0.7, 0.85, 12),
            _e("us_economy", "sector_it", 0.68, 0.84, 15, notes="US demand cycle for IT services"),
        ],
    },
    "metals": {
        "sector": "metals",
        "chain": ["china_economy", "copper", "steel", "metal_margins", "metal_earnings", "sector_metals"],
        "narrative": "China → Commodity Prices → Margins → Earnings",
        "edges": [
            _e("china_economy", "sector_metals", 0.8, 0.9, 15),
            _e("metal_earnings", "sector_metals", 0.82, 0.91, 12),
        ],
    },
    "fmcg": {
        "sector": "fmcg",
        "chain": ["inr", "imported_inflation", "consumer_spending", "fmcg_margins", "sector_fmcg"],
        "narrative": "Rupee / inflation → Spending → Margins",
        "edges": [
            _e("fmcg_margins", "sector_fmcg", 0.75, 0.88, 12),
            _e("fmcg_margins", "fmcg_multiple", 0.62, 0.8, 10),
            _e("agriculture", "fmcg_margins", 0.55, 0.78, 12, sign=-1, notes="Input cost pressure"),
        ],
    },
    "consumer_internet": {
        "sector": "consumer_internet",
        "chain": ["demand", "orders", "contribution_margin", "fcf", "sector_consumer_internet"],
        "narrative": "Demand → Orders → Contribution Margin → FCF",
        "edges": [
            _e("demand", "sector_consumer_internet", 0.76, 0.85, 8),
            _e("fcf", "sector_consumer_internet", 0.7, 0.84, 8),
        ],
    },
}


def model_for_sector(sector: str) -> dict[str, Any] | None:
    key = (sector or "").lower().replace(" ", "_")
    aliases = {
        "banks": "banks",
        "bank": "banks",
        "nbfc": "banks",
        "it": "it_services",
        "it_services": "it_services",
        "information_technology": "it_services",
        "metals": "metals",
        "steel": "metals",
        "fmcg": "fmcg",
        "consumer": "fmcg",
        "consumer_internet": "consumer_internet",
        "internet": "consumer_internet",
    }
    mid = aliases.get(key)
    return SECTOR_MODELS.get(mid) if mid else None
