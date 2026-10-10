"""Seed institutional universes — India Nifty family + global stubs.

Cross-universe support is first-class. Global universes are declared but not
claimed as covered until Tier-4 quality gates pass.
"""

from __future__ import annotations

from typing import Any

# Point-in-time membership events (fixture history for replay).
# effective_from inclusive; effective_to None = still a member.
MEMBERSHIP_EVENTS: list[dict[str, Any]] = [
    # Illustrative reconstitutions — never invent live index history beyond fixtures.
    {
        "event_id": "zomat_join_n100_2021",
        "ticker": "ZOMATO",
        "universe_id": "NIFTY_100",
        "action": "join",
        "effective_from": "2021-08-01",
        "effective_to": None,
        "source": "fixture_reconstitution",
        "note": "Consumer internet addition to large-cap watch",
    },
    {
        "event_id": "trent_join_n50_2024",
        "ticker": "TRENT",
        "universe_id": "NIFTY_50",
        "action": "join",
        "effective_from": "2024-03-28",
        "effective_to": None,
        "source": "fixture_reconstitution",
    },
    {
        "event_id": "yesbank_leave_n50_2020",
        "ticker": "YESBANK",
        "universe_id": "NIFTY_50",
        "action": "leave",
        "effective_from": "2005-01-01",
        "effective_to": "2020-03-27",
        "source": "fixture_reconstitution",
        "note": "Historical membership window then exit",
    },
    {
        "event_id": "persistent_join_n100_2022",
        "ticker": "PERSISTENT",
        "universe_id": "NIFTY_100",
        "action": "join",
        "effective_from": "2022-09-30",
        "effective_to": None,
        "source": "fixture_reconstitution",
    },
    {
        "event_id": "indigo_join_n100_2023",
        "ticker": "INDIGO",
        "universe_id": "NIFTY_100",
        "action": "join",
        "effective_from": "2023-03-31",
        "effective_to": None,
        "source": "fixture_reconstitution",
    },
]


def _csv_members(index_id: str, fallback: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Prefer live `indices/*.csv` constituents when present."""
    try:
        from market_indices.loader import list_members

        rows = list_members(index_id)
        symbols = [r["symbol"] for r in rows if r.get("symbol")]
        if symbols:
            return symbols
    except Exception:
        pass
    return list(fallback or [])


def universe_definitions() -> list[dict[str, Any]]:
    """Cross-universe registry definitions (India first; global declared)."""
    from institutional_reasoning.fundamentals.universe import NIFTY_50, NIFTY_100_EXTRA, GLOBAL_SEED
    from institutional_reasoning.fundamentals.nifty500_universe import NIFTY_500

    nifty_100_fallback = tuple(dict.fromkeys([*NIFTY_50, *NIFTY_100_EXTRA]))
    nifty_50 = _csv_members("NIFTY_50", NIFTY_50)
    nifty_next_50 = _csv_members("NIFTY_NEXT_50", [])
    nifty_100 = _csv_members("NIFTY_100", nifty_100_fallback)
    nifty_200 = _csv_members("NIFTY_200", nifty_100)
    nifty_500 = _csv_members("NIFTY_500", NIFTY_500)
    nifty_midcap_select = _csv_members("NIFTY_MIDCAP_SELECT", [])
    nifty_bank = _csv_members("NIFTY_BANK", [])
    nifty_fin = _csv_members("NIFTY_FINANCIAL_SERVICES", [])
    return [
        {
            "universe_id": "NIFTY_50",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": "NIFTY_100",
            "display_name": "Nifty 50",
            "tier": 1,
            "members": nifty_50,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/Nifty50.csv",
        },
        {
            "universe_id": "NIFTY_NEXT_50",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": "NIFTY_100",
            "display_name": "Nifty Next 50",
            "tier": 1,
            "members": nifty_next_50,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/NiftyNext50.csv",
        },
        {
            "universe_id": "NIFTY_100",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": "NIFTY_200",
            "display_name": "Nifty 100",
            "tier": 1,
            "members": nifty_100,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/Nifty100.csv",
        },
        {
            "universe_id": "NIFTY_200",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": "NIFTY_500",
            "display_name": "Nifty 200",
            "tier": 2,
            "members": nifty_200,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/Nifty200.csv",
        },
        {
            "universe_id": "NIFTY_500",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": "NIFTY_1000",
            "display_name": "Nifty 500",
            "tier": 2,
            "members": nifty_500,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/Nifty500.csv",
        },
        {
            "universe_id": "NIFTY_MIDCAP_SELECT",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": "NIFTY_500",
            "display_name": "Nifty Midcap Select",
            "tier": 2,
            "members": nifty_midcap_select,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/NiftyMidcapSelect.csv",
        },
        {
            "universe_id": "NIFTY_BANK",
            "family": "india_thematic",
            "region": "IN",
            "market": "NSE",
            "parent": None,
            "display_name": "Nifty Bank",
            "tier": 2,
            "members": nifty_bank,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/NiftyBank.csv",
        },
        {
            "universe_id": "NIFTY_FINANCIAL_SERVICES",
            "family": "india_thematic",
            "region": "IN",
            "market": "NSE",
            "parent": None,
            "display_name": "Nifty Financial Services",
            "tier": 2,
            "members": nifty_fin,
            "status": "active",
            "quality_standard": "institutional_depth",
            "source": "indices/NiftyFinancialServices.csv",
        },
        {
            "universe_id": "NIFTY_IT",
            "family": "india_thematic",
            "region": "IN",
            "market": "NSE",
            "parent": None,
            "display_name": "Nifty IT",
            "tier": 3,
            "members": ["INFY", "TCS", "HCLTECH", "WIPRO", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS", "OFSS"],
            "status": "active",
            "quality_standard": "institutional_depth",
        },
        {
            "universe_id": "NIFTY_1000",
            "family": "india_nifty",
            "region": "IN",
            "market": "NSE",
            "parent": None,
            "display_name": "Nifty 1000 (declared)",
            "tier": 3,
            "members": list(nifty_500),  # declared shell — expand without claiming coverage
            "status": "declared",
            "quality_standard": "institutional_depth",
            "note": "Declared path only; institutional coverage not claimed beyond Tier-2 quality gate.",
        },
        {
            "universe_id": "SPX",
            "family": "global_large_cap",
            "region": "US",
            "market": "NYSE/NASDAQ",
            "parent": None,
            "display_name": "S&P 500",
            "tier": 4,
            "members": list(GLOBAL_SEED),
            "status": "declared",
            "quality_standard": "institutional_depth",
            "note": "Tier 4 deferred — architecture ready, coverage not claimed.",
        },
        {
            "universe_id": "NDX",
            "family": "global_large_cap",
            "region": "US",
            "market": "NASDAQ",
            "parent": None,
            "display_name": "Nasdaq-100",
            "tier": 4,
            "members": [t for t in GLOBAL_SEED if t in {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META"}],
            "status": "declared",
            "quality_standard": "institutional_depth",
        },
        {
            "universe_id": "UKX",
            "family": "global_large_cap",
            "region": "GB",
            "market": "LSE",
            "parent": None,
            "display_name": "FTSE 100",
            "tier": 4,
            "members": [],
            "status": "declared",
            "quality_standard": "institutional_depth",
        },
        {
            "universe_id": "SX5E",
            "family": "global_large_cap",
            "region": "EU",
            "market": "EURONEXT",
            "parent": None,
            "display_name": "Euro Stoxx 50",
            "tier": 4,
            "members": [],
            "status": "declared",
            "quality_standard": "institutional_depth",
        },
        {
            "universe_id": "NKY",
            "family": "global_large_cap",
            "region": "JP",
            "market": "TSE",
            "parent": None,
            "display_name": "Nikkei 225",
            "tier": 4,
            "members": [],
            "status": "declared",
            "quality_standard": "institutional_depth",
        },
    ]
