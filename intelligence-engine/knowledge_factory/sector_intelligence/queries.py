"""Sector Intelligence query surface — institutional questions, not raw stats."""

from __future__ import annotations

from typing import Any

from knowledge_factory.sector_intelligence import store as isi_store
from knowledge_factory.sector_intelligence.macro_map import sectors_benefiting_from
from knowledge_factory.sector_intelligence.producers.core import (
    produce_cross_sector_rankings,
    produce_framework_mapping,
    produce_sector_valuation,
    relative_company_vs_sector,
)
from knowledge_factory.sector_intelligence.schema import SECTOR_UNIVERSE, canonicalize


def is_expensive_vs_sector_history(ticker: str, sector: str | None = None) -> dict[str, Any]:
    return relative_company_vs_sector(ticker, sector)


def should_use_dcf(ticker: str, sector: str | None = None) -> dict[str, Any]:
    """Framework mapping — e.g. HDFC Bank → Residual Income, not traditional DCF."""
    try:
        from knowledge_factory.fixtures.seed import sector_map

        sector = sector or sector_map().get(ticker.upper())
    except Exception:
        pass
    key = canonicalize(sector)
    if not key:
        return {
            "found": False,
            "ticker": ticker.upper(),
            "reason": "sector_history_unavailable",
            "fabricated": False,
            "insufficient": True,
        }
    mapping = produce_framework_mapping(key)
    preferred = mapping.get("preferred_frameworks") or []
    forbidden = mapping.get("forbidden_frameworks") or []
    dcf_forbidden = any("dcf" in f and "traditional" in f for f in forbidden) or "traditional_dcf" in forbidden
    primary = preferred[0] if preferred else None
    return {
        "found": True,
        "ticker": ticker.upper(),
        "sector": key,
        "should_use_traditional_dcf": bool(mapping.get("dcf_allowed")) and not dcf_forbidden and primary == "dcf",
        "primary_framework": primary,
        "preferred_frameworks": preferred,
        "forbidden_frameworks": forbidden,
        "residual_income_preferred": mapping.get("residual_income_preferred"),
        "recommendation": (
            "Use Residual Income / P/B — avoid traditional DCF as primary"
            if mapping.get("residual_income_preferred")
            else f"Preferred primary framework: {primary}"
        ),
        "framework_note": mapping.get("framework_note"),
        "fabricated": False,
    }


def sectors_outperform_when_rates_fall() -> dict[str, Any]:
    return sectors_benefiting_from("lower_rates", min_score=1)


def sector_valuation_during(sector: str, year: int) -> dict[str, Any]:
    key = canonicalize(sector)
    if not key:
        return {"found": False, "reason": "sector_history_unavailable", "fabricated": False, "insufficient": True}
    obj = isi_store.get_object(key)
    val = (obj or {}).get("historical_valuation") or produce_sector_valuation(key)
    hist = val.get("historical_median_pe") or {}
    fy_keys = [f"FY{year % 100:02d}", f"FY{(year + 1) % 100:02d}"]
    selected = {k: hist[k] for k in fy_keys if k in hist}
    if not selected and not hist:
        return {
            "found": False,
            "sector": key,
            "year": year,
            "reason": "sector_history_unavailable",
            "fabricated": False,
            "insufficient": True,
        }
    return {
        "found": True,
        "sector": key,
        "year": year,
        "valuation": selected or hist,
        "source": "historical_sector_replay",
        "fabricated": False,
    }


def strongest_roic_sector() -> dict[str, Any]:
    rankings = isi_store.get_rankings() or produce_cross_sector_rankings(list(SECTOR_UNIVERSE))
    top = rankings.get("strongest_roic_sector") or (rankings.get("roic_ranking") or [None])[0]
    if not top:
        return {"found": False, "reason": "sector_history_unavailable", "fabricated": False, "insufficient": True}
    return {
        "found": True,
        "sector": top.get("sector"),
        "roic": top.get("roic"),
        "ranking": rankings.get("roic_ranking") or [],
        "evidence": "historical_ranking",
        "fabricated": False,
    }


def sectors_resembling_regime(regime_id: str = "rate_hike_2022_23") -> dict[str, Any]:
    """Map today's-like macro regime to sectors via macro relationships + cycle tags."""
    # Rate hiking → hurt rate-sensitive; COVID → defensive / IT resilient etc.
    if "rate_hike" in regime_id or "rate_hiking" in regime_id:
        hurt = sectors_benefiting_from("higher_rates", min_score=1)
        helped = sectors_benefiting_from("lower_rates", min_score=2)
        return {
            "found": True,
            "regime_id": regime_id,
            "resembles": "rate_hiking_cycle",
            "sectors_that_benefit": hurt.get("sectors") or [],
            "sectors_hurt_when_opposite": helped.get("sectors") or [],
            "note": "Rate-hiking regimes historically support bank NIMs with lag; hurt auto/real_estate/NBFCs.",
            "fabricated": False,
        }
    if "covid" in regime_id:
        return {
            "found": True,
            "regime_id": regime_id,
            "resembles": "covid_shock",
            "sectors_that_benefit": [
                {"sector": "it_services", "score": 1, "note": "remote delivery"},
                {"sector": "pharma", "score": 1},
                {"sector": "fmcg", "score": 1},
            ],
            "sectors_hurt": [
                {"sector": "auto", "score": -2},
                {"sector": "aviation", "score": -2},
                {"sector": "real_estate", "score": -1},
            ],
            "fabricated": False,
        }
    return {
        "found": True,
        "regime_id": regime_id,
        "resembles": "generic",
        "sectors_that_benefit": sectors_benefiting_from("gdp_growth").get("sectors") or [],
        "fabricated": False,
    }


def get_playbook(sector: str) -> dict[str, Any]:
    from knowledge_factory.sector_intelligence.playbooks.catalog import sector_playbook

    key = canonicalize(sector)
    if not key:
        return {"found": False, "reason": "sector_history_unavailable", "fabricated": False}
    return {"found": True, **sector_playbook(key)}
