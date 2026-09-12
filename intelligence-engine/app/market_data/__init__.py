"""WS02 Market Data Platform (WBS DATA-001–005).

Institutional market-data access layer. Engines must consume canonical
objects from MarketDataClient only — never provider-native payloads.
"""

from app.market_data.client import MarketDataClient
from app.market_data.models import (
    CalendarEvent,
    CorporateAction,
    EconomicSeries,
    FundamentalSnapshot,
    MarketDataQuote,
    OHLCVBar,
    OHLCVSeries,
    OptionChain,
)

__all__ = [
    "MarketDataClient",
    "MarketDataQuote",
    "OHLCVBar",
    "OHLCVSeries",
    "CorporateAction",
    "FundamentalSnapshot",
    "OptionChain",
    "EconomicSeries",
    "CalendarEvent",
]
