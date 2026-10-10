"""Knowledge Compiler — ingest → normalise → derive → assemble CompanyMemory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from company_memory.derive import (
    derive_corporate_history,
    derive_event_timeline,
    derive_financial_history,
    derive_ownership_history,
    derive_price_intelligence,
    derive_sector_history,
    derive_valuation_history,
)
from company_memory.resolve import display_ticker, resolve_ticker
from company_memory.schema import (
    ENGINE_CODE,
    MEMORY_SECTIONS,
    SOURCE_INTELLIGENCE_MAP,
    VERSION,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_live_packs(
    entity: str,
    *,
    force: bool,
    skip_live: bool,
    injected: dict[str, Any] | None,
) -> dict[str, Any]:
    if injected:
        return {
            "market": injected.get("market"),
            "ownership": injected.get("ownership"),
            "earnings": injected.get("earnings"),
            "valuation": injected.get("valuation"),
        }
    if skip_live:
        return {}
    out: dict[str, Any] = {}
    try:
        from live_market_context.production import analyse as market_analyse

        out["market"] = market_analyse(entity, force=force)
    except Exception as exc:  # noqa: BLE001
        out["market"] = {"ok": False, "error": str(exc)[:120]}
    try:
        from ownership_intelligence.production import analyse as ownership_analyse

        out["ownership"] = ownership_analyse(entity, xbrl_quarters=4, persist=True, force=force)
    except Exception as exc:  # noqa: BLE001
        out["ownership"] = {"ok": False, "error": str(exc)[:120]}
    try:
        from earnings_intelligence.production import analyse as earnings_analyse

        out["earnings"] = earnings_analyse(
            entity, quarterly_xbrl=4, annual_xbrl=5, persist=True, force=force
        )
    except Exception as exc:  # noqa: BLE001
        out["earnings"] = {"ok": False, "error": str(exc)[:120]}
    try:
        from valuation_intelligence.production import analyse as valuation_analyse

        out["valuation"] = valuation_analyse(entity, max_peers=4, persist=True, force=force)
    except Exception as exc:  # noqa: BLE001
        out["valuation"] = {"ok": False, "error": str(exc)[:120]}
    return out


def _coverage(memory: dict[str, Any]) -> dict[str, Any]:
    flags = {
        "price_intelligence": bool((memory.get("price_intelligence") or {}).get("available")),
        "financial_history": bool((memory.get("financial_history") or {}).get("available")),
        "ownership_history": bool((memory.get("ownership_history") or {}).get("available")),
        "valuation_history": bool((memory.get("valuation_history") or {}).get("available")),
        "event_timeline": bool((memory.get("event_timeline") or {}).get("available")),
        "corporate_history": bool((memory.get("corporate_history") or {}).get("available")),
        "sector_history": bool((memory.get("sector_history") or {}).get("available")),
        "latest_evidence": bool(memory.get("latest_evidence")),
    }
    hit = sum(1 for v in flags.values() if v)
    return {
        "flags": flags,
        "sections_available": hit,
        "sections_total": len(flags),
        "coverage_pct": round(100.0 * hit / max(1, len(flags)), 1),
    }


def compile_company_memory(
    ticker: str,
    *,
    force: bool = False,
    skip_live: bool = False,
    allow_live_prices: bool = True,
    injected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compile persistent CompanyMemory for one ticker.

    Pipeline: ingest live packs (or injection) → derive intelligence objects →
    assemble versioned memory. Does not ask an LLM to rediscover facts.
    """
    t0 = datetime.now(timezone.utc)
    display = display_ticker(ticker)
    entity = resolve_ticker(ticker)

    packs = _fetch_live_packs(entity, force=force, skip_live=skip_live, injected=injected)
    ownership = packs.get("ownership") if isinstance(packs.get("ownership"), dict) else {}
    earnings = packs.get("earnings") if isinstance(packs.get("earnings"), dict) else {}
    valuation = packs.get("valuation") if isinstance(packs.get("valuation"), dict) else {}
    market = packs.get("market") if isinstance(packs.get("market"), dict) else {}

    price = derive_price_intelligence(entity, allow_live=allow_live_prices)
    financial = derive_financial_history(entity, earnings_pack=earnings)
    ownership_hist = derive_ownership_history(entity, ownership_pack=ownership)
    events = derive_event_timeline(entity, earnings_pack=earnings)
    corporate = derive_corporate_history(entity, event_timeline=events)
    sector = derive_sector_history(entity)
    val_hist = derive_valuation_history(entity, valuation_pack=valuation)

    # Risk history soft from price drawdowns + valuation stretch
    risk = {
        "available": bool(price.get("available") or val_hist.get("available")),
        "drawdown": (price.get("drawdown") or {}),
        "valuation_stretch": ((val_hist.get("historical_bands") or {}).get("pe") or {}).get("percentile"),
        "pledge": (ownership_hist.get("latest") or {}).get("pledge"),
        "leverage": ((financial.get("debt") or {}).get("debt_to_equity")),
        "lineage": [{"source": "price_intelligence|valuation_history|ownership_history"}],
    }

    latest_evidence = {
        "market": {
            "ltp": market.get("ltp"),
            "provider": market.get("provider"),
            "as_of": market.get("as_of"),
            "ok": market.get("ok"),
        },
        "ownership_ok": ownership.get("ok"),
        "earnings_coverage_pct": earnings.get("coverage_pct"),
        "valuation_ok": valuation.get("ok"),
        "valuation_stance": valuation.get("stance"),
        "freshness": {
            "market": market.get("as_of"),
            "ownership": ownership.get("as_of_quarter") or (ownership.get("freshness") or {}).get("as_of"),
            "earnings": (earnings.get("freshness") or {}).get("as_of") or (earnings.get("latest_quarter") or {}).get("period_end"),
            "valuation": (valuation.get("freshness") or {}).get("as_of"),
        },
    }

    # Soft competitive / business model stubs from sector + peers
    peers = (val_hist.get("peers") or {})
    business_model = {
        "sector": sector.get("sector_key"),
        "industry": peers.get("industry"),
        "sub_industry": None,
        "peer_universe": peers.get("primary") or [],
        "source": "valuation_peer_registry|sector_history",
    }
    competitive = {
        "peer_universe": peers.get("primary") or [],
        "relative_valuation": (val_hist.get("relative") or {}).get("pe"),
        "quality_signals": {
            "roe": (financial.get("returns") or {}).get("roe"),
            "cash_conversion": (financial.get("cash_flow") or {}).get("quality_ocf_to_pat"),
        },
        "observations": val_hist.get("observations") or [],
    }

    memory = {
        "kind": "company_memory",
        "engine": ENGINE_CODE,
        "version": VERSION,
        "display": display,
        "entity": entity,
        "compiled_at": _now(),
        "business_model": business_model,
        "competitive_position": competitive,
        "financial_history": financial,
        "ownership_history": ownership_hist,
        "valuation_history": val_hist,
        "corporate_history": corporate,
        "risk_history": risk,
        "sector_history": sector,
        "event_timeline": events,
        "price_intelligence": price,
        "latest_evidence": latest_evidence,
        "source_map": dict(SOURCE_INTELLIGENCE_MAP),
        "sections": list(MEMORY_SECTIONS),
        "recommendation_policy": "memory_only_no_buy_sell",
        "modifies_decision_engine": False,
    }
    cov = _coverage(memory)
    memory["coverage"] = cov
    memory["ok"] = cov["coverage_pct"] >= 50.0
    memory["confidence"] = round(min(0.95, 0.35 + cov["coverage_pct"] / 100.0 * 0.6), 3)
    memory["latency_ms"] = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    memory["lineage"] = [
        {"source": "live_market_context", "ok": bool(market.get("ok"))},
        {"source": "ownership_intelligence", "ok": bool(ownership.get("ok"))},
        {"source": "earnings_intelligence", "ok": bool(earnings.get("ok"))},
        {"source": "valuation_intelligence", "ok": bool(valuation.get("ok"))},
        {"source": "historical_depth", "ref": "prices|timeline|derived"},
        {"source": "peer_intelligence", "ref": "living_packs"},
    ]
    return memory
