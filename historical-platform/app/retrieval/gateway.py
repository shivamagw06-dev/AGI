"""Historical Retrieval Gateway — store only, never call external providers."""

from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.coverage.policy import policy_snapshot
from app.hko.shape import shape_hko_view
from app.hai.engine import HistoricalAnalogueEngine
from app.hri.engine import HistoricalRelationshipEngine
from app.storage.db import HipStore
from app.timeline import traces
from app.timeline.builder import TimelineBuilder
from app.contracts.models import HistoricalObjectType


class HistoricalRetrievalGateway:
    def __init__(self, store: HipStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.timelines = TimelineBuilder(store)
        self.relationships = HistoricalRelationshipEngine(store)
        self.analogues = HistoricalAnalogueEngine(store)

    def company_history(self, symbol: str) -> dict[str, Any]:
        span = traces.begin("historical_retrieval", meta={"symbol": symbol, "kind": "company"})
        symbol = symbol.upper()
        entity = self.store.get_entity(symbol)
        timeline = self.store.get_timeline("company", symbol)
        if not timeline:
            timeline = self.timelines.build_company_timeline(symbol, persist=True)
        out = {
            "company_symbol": symbol,
            "entity": entity,
            "providers_queried": [],
            "timeline": timeline,
            "profiles": self.store.list_profiles(symbol),
            "prices_daily": self.store.list_prices(symbol, period_kind="daily", limit=5000),
            "financials": self.financials(symbol),
            "dividends": self.store.list_dividends(symbol),
            "actions": self.store.list_actions(symbol),
            "events": self.events(symbol),
            "reports": self.store.list_reports(symbol),
            "news": self.store.list_news(symbol),
            "coverage": self.store.coverage_report(symbol, self.settings),
            "timeline_completeness": self.store.timeline_completeness(symbol),
            "relationships": self.store.list_timeline_links(symbol),
        }
        traces.end(span, output={"timeline_events": len(timeline)})
        return out

    def timeline(self, symbol: str) -> dict[str, Any]:
        span = traces.begin("historical_retrieval", meta={"symbol": symbol, "kind": "timeline"})
        symbol = symbol.upper()
        events = self.store.get_timeline("company", symbol)
        if not events:
            events = self.timelines.build_company_timeline(symbol, persist=True)
        entity = self.store.get_entity(symbol)
        out = {
            "company_symbol": symbol,
            "entity": entity,
            "providers_queried": [],
            "timeline": events,
            "narrative": [
                {"year": e.get("year"), "title": e.get("title"), "importance": e.get("importance")}
                for e in events
            ],
            "relationships": self.store.list_timeline_links(symbol),
            "completeness": self.store.timeline_completeness(symbol),
        }
        traces.end(span, output={"count": len(events)})
        return out

    def sector_timeline(self, sector_key: str) -> dict[str, Any]:
        sector_key = sector_key.lower().replace(" ", "_")
        events = self.store.get_timeline("sector", sector_key)
        if not events:
            events = self.timelines.build_sector_timeline(sector_key, persist=True)
        return {
            "sector_key": sector_key,
            "providers_queried": [],
            "timeline": events,
            "narrative": [
                {"year": e.get("year"), "title": e.get("title"), "importance": e.get("importance")}
                for e in events
            ],
        }

    def market_timeline(self) -> dict[str, Any]:
        events = self.store.get_timeline("market", "nifty")
        if not events:
            events = self.timelines.build_market_timeline(persist=True)
        return {
            "market": "NIFTY",
            "providers_queried": [],
            "timeline": events,
            "narrative": [
                {"year": e.get("year"), "title": e.get("title"), "importance": e.get("importance")}
                for e in events
            ],
        }

    def macro_timeline(self) -> dict[str, Any]:
        events = self.store.get_timeline("macro", "india")
        if not events:
            events = self.timelines.build_macro_timeline(persist=True)
        return {
            "macro": "India",
            "providers_queried": [],
            "timeline": events,
            "narrative": [
                {"year": e.get("year"), "title": e.get("title"), "importance": e.get("importance")}
                for e in events
            ],
        }

    def financials(self, symbol: str, *, period_kind: str | None = None) -> list[dict[str, Any]]:
        rows = self.store.list_financials(symbol, period_kind=period_kind)
        return [
            {
                **row,
                "hko": shape_hko_view(HistoricalObjectType.FINANCIAL_STATEMENT, row),
            }
            for row in rows
        ]

    def events(self, symbol: str) -> list[dict[str, Any]]:
        rows = self.store.list_events(symbol)
        return [
            {
                **row,
                "hko": shape_hko_view(HistoricalObjectType.CORPORATE_EVENT, row),
            }
            for row in rows
        ]

    def compare(
        self,
        symbol: str,
        *,
        as_of_period: str = "FY2018",
        include_current_tip: bool = True,
    ) -> dict[str, Any]:
        """Compare a historical period with latest available knowledge — store only.

        Success path: Compare Infosys today with FY2018.
        """
        span = traces.begin(
            "historical_retrieval",
            meta={"symbol": symbol, "kind": "compare", "as_of": as_of_period},
        )
        symbol = symbol.upper()
        fins = self.financials(symbol, period_kind="annual")
        historical = next((f for f in fins if f.get("effective_date") == as_of_period), None)
        # Latest annual period as "today" tip from historical store (not live Yahoo)
        current = fins[-1] if fins else None
        timeline = self.timeline(symbol)
        # Events around the as-of year
        year = None
        if as_of_period.startswith("FY") and len(as_of_period) >= 6:
            try:
                year = int(as_of_period[2:6])
            except ValueError:
                year = None
        period_events = [
            e
            for e in timeline.get("timeline") or []
            if year is None or int(e.get("year") or 0) == year or abs(int(e.get("year") or 0) - (year or 0)) <= 1
        ]
        out = {
            "company_symbol": symbol,
            "providers_queried": [],
            "as_of_period": as_of_period,
            "historical_financials": historical,
            "current_company_knowledge_tip": current if include_current_tip else None,
            "historical_timeline": timeline.get("timeline"),
            "period_events": period_events,
            "entity": self.store.get_entity(symbol),
            "bundle": {
                "current_company_knowledge": current.get("hko") if current else None,
                "historical_timeline": timeline.get("narrative"),
                "historical_financials": (historical or {}).get("hko"),
                "historical_events": [
                    shape_hko_view(HistoricalObjectType.CORPORATE_EVENT, e)
                    if "knowledge" in e
                    else e
                    for e in period_events
                ],
            },
            "note": "KRIG/Ask should consume this bundle — zero external provider calls.",
        }
        traces.end(span, output={"found_historical": historical is not None})
        return out

    def revenue_growth(
        self,
        symbol: str,
        *,
        from_period: str = "FY2015",
        to_period: str = "FY2025",
    ) -> dict[str, Any]:
        series = self.store.revenue_series(symbol, from_period=from_period, to_period=to_period)
        growth = []
        prev = None
        for row in series:
            rev = row.get("revenue")
            yoY = None
            if prev and prev.get("revenue") and rev:
                yoY = round((float(rev) - float(prev["revenue"])) / float(prev["revenue"]) * 100, 2)
            growth.append({**row, "revenue_growth_pct": yoY})
            prev = row
        return {
            "company_symbol": symbol.upper(),
            "from_period": from_period,
            "to_period": to_period,
            "providers_queried": [],
            "series": growth,
            "entity": self.store.get_entity(symbol),
            "note": "Retrieved exclusively from Historical Knowledge Store.",
        }

    def coverage(self, symbol: str) -> dict[str, Any]:
        return self.store.coverage_report(symbol, self.settings)

    def policy(self) -> dict[str, Any]:
        return policy_snapshot(self.settings)

    def mission_control(self) -> dict[str, Any]:
        symbols = list(self.settings.watchlist) or self.store.list_entity_symbols()
        rows = []
        for symbol in symbols:
            cov = self.store.coverage_report(symbol, self.settings)
            tl = self.store.timeline_completeness(symbol)
            years = tl.get("years_ingested") or []
            rel_n = len(self.store.list_relationships(company_symbol=symbol))
            rows.append(
                {
                    "company_symbol": symbol,
                    "coverage_status": {
                        k: v.get("status") for k, v in (cov.get("categories") or {}).items()
                    },
                    "timeline_completeness": tl.get("status"),
                    "timeline_events": tl.get("timeline_events"),
                    "years_ingested": years,
                    "years_span": tl.get("years_span"),
                    "missing_periods": tl.get("missing_periods"),
                    "relationship_count": rel_n,
                }
            )
        runs = self.store.list_runs(limit=10)
        hri = self.store.relationship_dashboard()
        hai = self.store.analogue_dashboard()
        return {
            "board": "Historical Intelligence",
            "version": self.settings.version,
            "companies": rows,
            "timeline_events_total": self.store.count_timeline_events(),
            "historical_objects": self.store.count_objects(),
            "raw_archive": self.store.count_raw(),
            "ingestion_progress": runs,
            "relationships": hri,
            "relationship_board": {
                "title": "Historical Relationship Intelligence",
                **hri,
            },
            "analogue_board": {
                "title": "Historical Analogue Intelligence",
                **hai,
            },
            "retrieval_performance": {
                "providers_queried_always": [],
                "traces": traces.recent(80),
            },
            "principles": {
                "immutable_history": True,
                "providers_never_on_ask_path": True,
                "narratives_not_rows": True,
                "no_relationship_without_evidence": True,
                "no_analogue_without_explainable_score": True,
            },
        }
