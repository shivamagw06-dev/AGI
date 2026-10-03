"""Seed research notes that become Intelligence Hubs (AGI-owned catalog)."""

from __future__ import annotations

from typing import Any

SEED_NOTES: list[dict[str, Any]] = [
    {
        "id": "rih_rbi_easing_watch",
        "headline": "RBI easing optionality and India equity breadth",
        "publication_date": "2026-07-28",
        "session": "Morning",
        "body": (
            "Inflation moderation keeps RBI rate-cut optionality alive. "
            "Liquidity conditions and FII flows remain the key transmission channels "
            "into Banking and Capital Goods. Nifty breadth and midcap participation "
            "will determine whether the bull market extends. Compare with previous "
            "RBI cycles and the 2013 Taper Tantrum for risk paths. "
            "ICICIBANK and HDFCBANK lead the financials response; LT tracks capex."
        ),
        "tickers": ["ICICIBANK", "HDFCBANK", "LT"],
        "importance_score": 88,
    },
    {
        "id": "rih_it_usd_sensitivity",
        "headline": "IT Services: USDINR, deal momentum and margin defence",
        "publication_date": "2026-07-27",
        "session": "Afternoon",
        "body": (
            "US demand and currency remain the dual drivers for IT Services. "
            "INFY and TCS commentary on deal wins, attrition and pricing will set "
            "the sector path. A stronger dollar historically supports INR revenues "
            "but global bond yields can compress multiples. Watch Nasdaq risk "
            "sentiment and Fed policy as global links."
        ),
        "tickers": ["INFY", "TCS", "HCLTECH"],
        "importance_score": 82,
    },
    {
        "id": "rih_capex_defence_cycle",
        "headline": "Government capex and Defence / Capital Goods leadership",
        "publication_date": "2026-07-26",
        "session": "Pre Market",
        "body": (
            "Fiscal capex and Defence orders continue to shape Capital Goods "
            "leadership. LT and SIEMENS sit at the centre of order-book visibility. "
            "Steel and Auto supply chains are secondary beneficiaries. "
            "IPO activity in industrials remains a watchpoint for sector liquidity."
        ),
        "tickers": ["LT", "SIEMENS"],
        "importance_score": 79,
    },
    {
        "id": "rih_global_risk_off",
        "headline": "Global yields, oil spike risk and EM equity transmission",
        "publication_date": "2026-07-25",
        "session": "Global",
        "body": (
            "Rising US Treasury yields and oil price spikes remain the primary "
            "global risk-off channels into India. Currency depreciation and FII "
            "outflows historically accompany such regimes. Compare COVID recovery "
            "and 2008 Financial Crisis analogues for breadth and liquidity paths."
        ),
        "tickers": ["RELIANCE"],
        "importance_score": 85,
    },
]


def list_seeds() -> list[dict[str, Any]]:
    return list(SEED_NOTES)


def get_seed(note_id: str) -> dict[str, Any] | None:
    for n in SEED_NOTES:
        if n["id"] == note_id:
            return dict(n)
    # Allow slug match on headline fragment
    key = note_id.lower().replace("-", "_")
    for n in SEED_NOTES:
        if key in n["id"] or key in n["headline"].lower().replace(" ", "_"):
            return dict(n)
    return None
