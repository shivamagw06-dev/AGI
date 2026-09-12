"""Historical collectors — live Yahoo first (when enabled), fixture fallback."""

from __future__ import annotations

import os
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.fixtures.seed_history import (
    annual_records,
    corporate_action_records,
    macro_history,
    market_regimes,
    monthly_prices,
    quarterly_records,
    seed_universe,
    shareholding_records,
    timeline_records,
)


def _live_on() -> bool:
    # Default off for offline tests; enable in production via render.yaml / CGL.
    return str(os.getenv("KF_HD_LIVE_COLLECTORS", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def collect_entity_history(entity: str, *, prefer_live: bool | None = None) -> dict[str, Any]:
    e = entity.upper()
    use_live = _live_on() if prefer_live is None else prefer_live
    live_row: dict[str, Any] | None = None
    if use_live:
        try:
            from knowledge_factory.historical_depth.collectors.yahoo_live import collect_entity_live

            live_row = collect_entity_live(e)
        except Exception as exc:  # noqa: BLE001
            live_row = {"entity": e, "status": "error", "errors": [str(exc)[:200]], "source": "yahoo_live"}

    # Fixture seed still fills gaps (quarterly / timeline) without overwriting live PIT keys.
    annual = annual_records(e)
    quarterly = quarterly_records(e)
    prices = monthly_prices(e)
    actions = corporate_action_records(e)
    timeline = timeline_records(e)

    # Only seed fixtures when live produced nothing for that series (avoid diluting live years
    # with short fixture panels on a second write — put_series won't overwrite keys, but
    # fixture periods differ so they would inflate counts incorrectly).
    live_ok = bool(live_row and live_row.get("status") in {"ok", "degraded"} and (live_row.get("price_points") or 0) > 0)
    env = (os.getenv("APP_ENV") or os.getenv("AGIB_ENV") or "").strip().lower()
    allow_fixture_seed = env not in {"production", "prod"}
    if not live_ok and allow_fixture_seed:
        hd_store.put_series("financials_annual", e, annual)
        hd_store.put_series("prices", e, prices)
        hd_store.put_series("corporate_actions", e, actions)
        # Offline/tests only — production never seeds ownership fixtures
        hd_store.put_series("shareholding", e, shareholding_records(e))
        _seed_ir_fixture(e)
    # Production: never pad with fixture quarterlies. Dev/tests may opt-in.
    env = (os.getenv("APP_ENV") or os.getenv("AGIB_ENV") or "").strip().lower()
    fixture_default = "false" if env in {"production", "prod"} else "true"
    if str(os.getenv("KF_HD_FIXTURE_QUARTERLY", fixture_default)).lower() in {"1", "true", "yes", "on"}:
        hd_store.put_series("financials_quarterly", e, quarterly)
        hd_store.put_series("timeline", e, timeline)

    series_a = hd_store.get_series("financials_annual", e) or {}
    series_p = hd_store.get_series("prices", e) or {}
    years = max(len(series_a.get("records") or []), _price_years(series_p))
    return {
        "entity": e,
        "annual_periods": len(series_a.get("records") or []),
        "quarterly_periods": len((hd_store.get_series("financials_quarterly", e) or {}).get("records") or []),
        "price_points": len(series_p.get("records") or []),
        "timeline_events": len((hd_store.get_series("timeline", e) or {}).get("records") or []),
        "corporate_actions": len((hd_store.get_series("corporate_actions", e) or {}).get("records") or []),
        "history_years": years,
        "live": live_row,
        "status": "ok" if (live_ok or years > 0) else "error",
    }


def _seed_ir_fixture(entity: str) -> None:
    """Minimal IR document evidence for offline/tests (never production)."""
    try:
        from live_data import store as lidi_store

        e = entity.upper()
        existing = lidi_store.get_object("company_ir", e) or {}
        if existing.get("documents"):
            return
        lidi_store.put_object(
            "company_ir",
            e,
            {
                "documents": [
                    {
                        "doc_type": "annual_report",
                        "title": f"{e} Annual Report (fixture)",
                        "url": f"fixture://{e}/annual-report.pdf",
                    },
                    {
                        "doc_type": "quarterly_results",
                        "title": f"{e} Quarterly Results (fixture)",
                        "url": f"fixture://{e}/results.pdf",
                    },
                ],
                "source": "fixture",
            },
        )
    except Exception:
        pass


def _price_years(series: dict[str, Any]) -> float:
    records = list(series.get("records") or [])
    ends = [str(r.get("period_end") or "")[:10] for r in records if r.get("period_end")]
    if len(ends) < 2:
        return float(len(ends))
    try:
        from datetime import datetime

        d0 = datetime.fromisoformat(min(ends))
        d1 = datetime.fromisoformat(max(ends))
        return round((d1 - d0).days / 365.25, 2)
    except Exception:
        return float(len({e[:4] for e in ends}))


def collect_market_history() -> dict[str, Any]:
    regimes = market_regimes()
    macro = macro_history()
    hd_store.put_regimes(regimes)
    hd_store.put_macro_history(macro)
    return {"regimes": len(regimes), "macro_periods": len(macro), "status": "ok"}


def collect_universe(entities: list[str] | None = None) -> dict[str, Any]:
    """Collect history for a universe.

    Live Yahoo fetches are rate-limited: only entities still below target years
    are fetched, capped by KF_HD_BACKFILL_BATCH (default 12). Remaining names
    keep existing store data / fixture fill without re-downloading.
    """
    entities = entities or seed_universe()
    market = collect_market_history()
    batch_cap = max(1, int(os.getenv("KF_HD_BACKFILL_BATCH") or "12"))
    target = float(os.getenv("KF_HD_TARGET_YEARS") or "15")
    live_budget = batch_cap if _live_on() else 0
    rows = []
    live_used = 0
    for e in entities:
        prefer_live = False
        if live_used < live_budget:
            years = _price_years(hd_store.get_series("prices", e) or {})
            annual_n = len((hd_store.get_series("financials_annual", e) or {}).get("records") or [])
            if max(years, float(annual_n)) < target:
                prefer_live = True
                live_used += 1
        rows.append(collect_entity_history(e, prefer_live=prefer_live if _live_on() else False))
    return {
        "entities": len(rows),
        "market": market,
        "rows": rows,
        "status": "ok",
        "live_collectors": _live_on(),
        "live_fetched": live_used,
        "live_budget": live_budget,
    }
