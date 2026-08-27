"""Soft collectors for Corporate Event Intelligence.

Priority: curated ICEI seeds → Company Intelligence timeline → Historical Depth
timeline/actions → management pack leadership notes.
Never invent events absent from these sources.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.corporate_events.fixtures.seeds import get_event_seeds


def _sector(ticker: str) -> str | None:
    try:
        from knowledge_factory.nifty500_universe import NIFTY_500_SECTOR

        return NIFTY_500_SECTOR.get(ticker.upper())
    except Exception:
        return None


def _ici_timeline(ticker: str) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.company_intelligence import store as ici_store

        obj = ici_store.get(ticker)
        if not obj:
            return []
        tl = (obj.get("modules") or {}).get("timeline") or {}
        return list(tl.get("events") or [])
    except Exception:
        return []


def _ici_seed_timeline(ticker: str) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.company_intelligence.fixtures.seeds import get_seed

        seed = get_seed(ticker) or {}
        return list(seed.get("timeline") or [])
    except Exception:
        return []


def _hd_timeline(ticker: str) -> list[dict[str, Any]]:
    try:
        from knowledge_factory.historical_depth.fixtures.seed_history import (
            corporate_action_records,
            timeline_records,
        )

        events = list(timeline_records(ticker))
        for rec in corporate_action_records(ticker):
            payload = rec.get("payload") or {}
            events.append(
                {
                    "date": rec.get("period") or rec.get("available_from"),
                    "available_from": rec.get("available_from"),
                    "event_type": payload.get("action") or "corporate_action",
                    "title": f"Corporate action: {payload.get('action')}",
                    "source": "historical_depth_fixture",
                    "evidence": f"{ticker}-CA-{rec.get('period')}",
                    "confidence": 0.75,
                }
            )
        return events
    except Exception:
        return []


def collect_event_context(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").upper()
    seeds = get_event_seeds(t)
    return {
        "ticker": t,
        "sector": _sector(t),
        "seeds": seeds,
        "has_seed": bool(seeds),
        "ici_timeline": _ici_timeline(t),
        "ici_seed_timeline": _ici_seed_timeline(t),
        "hd_timeline": _hd_timeline(t),
        "sources_priority": [
            "nse_filings",
            "bse_filings",
            "company_announcements",
            "annual_reports",
            "investor_presentations",
            "earnings_transcripts",
            "sebi",
            "mca",
            "rbi",
            "institutional_event_seed",
            "historical_depth",
            "company_intelligence_timeline",
        ],
    }
