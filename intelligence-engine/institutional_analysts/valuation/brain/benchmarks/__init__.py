"""Valuation benchmarks — history, sector, markets, growth/capital quality overlays."""

from __future__ import annotations

from typing import Any

from institutional_analysts.valuation.brain._text import as_list, txt


def benchmark(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    hist = (frameworks.get("historical_valuation") or {}).get("assessment")
    peers = (frameworks.get("peer_comparison") or {}).get("assessment")
    assessment = (
        f"Benchmarking {name} against own history, sector peers, and broader market context — "
        "adjusted for growth profile and capital quality — never against a single multiple in isolation. "
        f"{hist or ''} {peers or ''}"
    ).strip()
    return {
        "historical_company_valuation": txt(evidence.get("historical")) or "Own history band",
        "sector_valuation": as_list(evidence.get("indian_peers"), limit=3) or ["Sector average multiples"],
        "indian_market": "Indian market valuation regime as qualitative backdrop",
        "global_market": "Global category valuation regime as qualitative backdrop",
        "risk_free_environment": "Discount-rate / risk-free backdrop treated qualitatively (no fabricated precision)",
        "growth_profile": (frameworks.get("market_expectations") or {}).get("implied_growth"),
        "capital_quality": (frameworks.get("market_expectations") or {}).get("implied_roic"),
        "never_self_only": True,
        "assessment": assessment,
    }
