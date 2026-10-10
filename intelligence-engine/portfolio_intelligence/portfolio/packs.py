"""Institutional portfolio memory — V1 seed books (not live brokerage sync)."""

from __future__ import annotations

from typing import Any

from portfolio_intelligence.schema import Holding, PortfolioProfile

PORTFOLIOS: dict[str, dict[str, Any]] = {
    "agib_core_india": {
        "profile": PortfolioProfile(
            portfolio_id="agib_core_india",
            name="AGIB Core India Equity",
            objective="Long-term compounding via high-quality India franchises",
            benchmark="Nifty 50 TRI",
            base_currency="INR",
            risk_tolerance="moderate",
            horizon="7y+",
            target_return="CPI+6% to CPI+8%",
            max_drawdown=0.28,
            liquidity_requirement="T+5 institutional",
            tax_preferences="long_term_capital_gains_aware",
            sector_limits={"banks": 0.35, "it_services": 0.25, "fmcg": 0.20, "consumer_internet": 0.15},
            single_name_limit=0.12,
        ).to_dict(),
        "holdings": [
            Holding(
                "HDFCBANK",
                0.11,
                "banks",
                "private_bank",
                "IN",
                "large",
                "quality",
                "Liability franchise rebuild + capital resilience",
                "high",
                "2024-03-15",
                1450.0,
                {"quality": 0.8, "value": 0.4, "growth": 0.5, "momentum": 0.3, "low_vol": 0.6, "dividend": 0.4, "leverage": 0.5, "profitability": 0.7},
            ).to_dict(),
            Holding(
                "ICICIBANK",
                0.09,
                "banks",
                "private_bank",
                "IN",
                "large",
                "quality",
                "Retail franchise + underwriting discipline",
                "high",
                "2023-11-01",
                920.0,
                {"quality": 0.75, "value": 0.45, "growth": 0.55, "momentum": 0.4, "low_vol": 0.55, "dividend": 0.35, "leverage": 0.55, "profitability": 0.72},
            ).to_dict(),
            Holding(
                "TCS",
                0.10,
                "it_services",
                "it_services",
                "IN",
                "large",
                "quality",
                "Cash-rich IT franchise, capital return discipline",
                "high",
                "2022-06-01",
                3200.0,
                {"quality": 0.9, "value": 0.35, "growth": 0.45, "momentum": 0.35, "low_vol": 0.7, "dividend": 0.55, "leverage": 0.15, "profitability": 0.9},
            ).to_dict(),
            Holding(
                "INFY",
                0.08,
                "it_services",
                "it_services",
                "IN",
                "large",
                "quality",
                "Digital services quality compounder",
                "medium",
                "2023-01-20",
                1400.0,
                {"quality": 0.85, "value": 0.4, "growth": 0.5, "momentum": 0.4, "low_vol": 0.65, "dividend": 0.5, "leverage": 0.2, "profitability": 0.85},
            ).to_dict(),
            Holding(
                "NESTLEIND",
                0.07,
                "fmcg",
                "staples",
                "IN",
                "large",
                "quality",
                "Pricing power + distribution moat",
                "medium",
                "2021-09-10",
                18000.0,
                {"quality": 0.88, "value": 0.2, "growth": 0.55, "momentum": 0.35, "low_vol": 0.75, "dividend": 0.45, "leverage": 0.2, "profitability": 0.88},
            ).to_dict(),
            Holding(
                "RELIANCE",
                0.08,
                "energy_conglomerate",
                "conglomerate",
                "IN",
                "large",
                "blend",
                "Energy + retail + digital platform optionality",
                "medium",
                "2022-02-01",
                2400.0,
                {"quality": 0.65, "value": 0.5, "growth": 0.6, "momentum": 0.45, "low_vol": 0.4, "dividend": 0.35, "leverage": 0.55, "profitability": 0.6},
            ).to_dict(),
            Holding(
                "BHARTIARTL",
                0.06,
                "telecom",
                "telecom",
                "IN",
                "large",
                "growth",
                "Industry consolidation + ARPU recovery",
                "medium",
                "2023-05-01",
                850.0,
                {"quality": 0.6, "value": 0.35, "growth": 0.7, "momentum": 0.55, "low_vol": 0.35, "dividend": 0.2, "leverage": 0.65, "profitability": 0.55},
            ).to_dict(),
            Holding(
                "ASIANPAINT",
                0.05,
                "fmcg",
                "decorative_paints",
                "IN",
                "large",
                "quality",
                "Brand + distribution pricing power",
                "medium",
                "2020-11-01",
                2800.0,
                {"quality": 0.85, "value": 0.25, "growth": 0.5, "momentum": 0.3, "low_vol": 0.7, "dividend": 0.4, "leverage": 0.15, "profitability": 0.82},
            ).to_dict(),
            Holding(
                "AXISBANK",
                0.05,
                "banks",
                "private_bank",
                "IN",
                "large",
                "blend",
                "Franchise recovery / underwriting watch",
                "low",
                "2024-08-01",
                1100.0,
                {"quality": 0.55, "value": 0.55, "growth": 0.5, "momentum": 0.4, "low_vol": 0.4, "dividend": 0.25, "leverage": 0.6, "profitability": 0.58},
            ).to_dict(),
            Holding(
                "ETERNAL",
                0.04,
                "consumer_internet",
                "food_delivery",
                "IN",
                "large",
                "growth",
                "Unit economics path + competitive intensity watch",
                "low",
                "2025-01-15",
                220.0,
                {"quality": 0.45, "value": 0.3, "growth": 0.85, "momentum": 0.6, "low_vol": 0.2, "dividend": 0.0, "leverage": 0.25, "profitability": 0.35},
            ).to_dict(),
        ],
        "cash_weight": 0.27,
        "watchlist": [
            {"ticker": "KOTAKBANK", "priority": "research", "note": "Private bank diversification vs HDFC/ICICI overlap"},
            {"ticker": "HINDUNILVR", "priority": "monitor", "note": "Staples quality; valuation discipline required"},
            {"ticker": "SBIN", "priority": "research", "note": "PSU bank — portfolio fit only if quality gates clear"},
        ],
        "benchmark_sector_weights": {
            "banks": 0.28,
            "it_services": 0.14,
            "fmcg": 0.10,
            "energy_conglomerate": 0.10,
            "telecom": 0.04,
            "consumer_internet": 0.03,
            "cash": 0.0,
        },
    }
}


def _warehouse_portfolio(portfolio_id: str) -> dict[str, Any] | None:
    """Load the latest complete immutable portfolio snapshot when one exists."""
    try:
        from institutional_warehouse import store

        snapshots = store.all_rows("portfolio_snapshots", entity=portfolio_id, limit=5000)
        eligible = [row for row in snapshots if str(row.get("status") or "ACTIVE").upper() in {"ACTIVE", "PUBLISHED"}]
        if not eligible:
            return None
        snapshot = max(eligible, key=lambda row: str(row.get("as_of") or ""))
        as_of = str(snapshot.get("as_of") or "")
        holdings = [
            row for row in store.all_rows("portfolio_holdings", entity=portfolio_id, limit=10000)
            if str(row.get("as_of") or "") == as_of
        ]
        if not holdings:
            return None
        returns = store.all_rows("portfolio_daily_returns", entity=portfolio_id, limit=10000)
        attribution = store.all_rows("portfolio_attribution", entity=portfolio_id, limit=100000)
    except Exception:
        return None

    weight_sum = sum(float(row.get("weight") or 0) for row in holdings)
    weights_valid = bool(holdings) and all(0 <= float(row.get("weight") or 0) <= 1 for row in holdings) and weight_sum <= 1.0001
    clean_holdings = []
    for row in holdings:
        clean_holdings.append({
            "ticker": str(row.get("ticker") or "").upper(),
            "weight": float(row.get("weight") or 0),
            "sector": row.get("sector") or "other",
            "industry": row.get("industry") or row.get("sector") or "other",
            "country": row.get("country") or "IN",
            "market_cap": "unknown",
            "style": "unknown",
            "conviction": row.get("conviction") or "unrated",
            "beta": row.get("beta"),
            "factors": row.get("factors") or {},
        })
    profile = {
        "portfolio_id": portfolio_id,
        "name": snapshot.get("name") or portfolio_id,
        "objective": snapshot.get("objective") or "Institutional research portfolio",
        "benchmark": snapshot.get("benchmark"),
        "base_currency": snapshot.get("base_currency") or "INR",
        "risk_tolerance": snapshot.get("risk_tolerance") or "moderate",
        "horizon": None,
        "target_return": None,
        "max_drawdown": float(snapshot.get("max_drawdown") or 0.25),
        "liquidity_requirement": None,
        "tax_preferences": None,
        "sector_limits": snapshot.get("sector_limits") or {},
        "single_name_limit": float(snapshot.get("single_name_limit") or 0.12),
    }
    return {
        "profile": profile,
        "holdings": clean_holdings,
        "cash_weight": float(snapshot.get("cash_weight") or max(0.0, 1.0 - weight_sum)),
        "watchlist": [],
        "benchmark_sector_weights": snapshot.get("benchmark_sector_weights") or {},
        "daily_returns": sorted(returns, key=lambda row: str(row.get("date") or "")),
        "attribution": sorted(attribution, key=lambda row: str(row.get("date") or "")),
        "data_lineage": {
            "source": "institutional_warehouse",
            "portfolio_as_of": as_of,
            "immutable_snapshot": True,
            "holdings": len(clean_holdings),
            "weights_valid": weights_valid,
            "weight_sum": round(weight_sum, 6),
            "daily_return_observations": len(returns),
            "attribution_observations": len(attribution),
            "empirical_risk_ready": len(returns) >= 252,
            "attribution_ready": len(attribution) > 0,
        },
    }


def list_portfolios() -> list[str]:
    ids = set(PORTFOLIOS)
    try:
        from institutional_warehouse import store

        ids.update(str(value) for value in store.entities("portfolio_snapshots") if value)
    except Exception:
        pass
    return sorted(ids)


def portfolio_for(portfolio_id: str) -> dict[str, Any] | None:
    pid = (portfolio_id or "").strip().lower().replace(" ", "_")
    aliases = {
        "default": "agib_core_india",
        "core": "agib_core_india",
        "india": "agib_core_india",
        "agib": "agib_core_india",
    }
    pid = aliases.get(pid, pid)
    warehouse = _warehouse_portfolio(pid)
    if warehouse:
        return warehouse
    p = PORTFOLIOS.get(pid)
    return {
        **dict(p),
        "data_lineage": {
            "source": "seed_research_pack",
            "portfolio_as_of": None,
            "immutable_snapshot": False,
            "holdings": len(p.get("holdings") or []),
            "weights_valid": True,
            "daily_return_observations": 0,
            "attribution_observations": 0,
            "empirical_risk_ready": False,
            "attribution_ready": False,
        },
    } if p else None


def default_portfolio_id() -> str:
    try:
        from institutional_warehouse import store

        live = sorted(str(value) for value in store.entities("portfolio_snapshots") if value)
        if "agib_core_india" in live:
            return "agib_core_india"
        if live:
            return live[0]
    except Exception:
        pass
    return "agib_core_india"
