"""Soft-wire real universe/coverage data into IKT — never fabricated.

`sync_company_master` writes only fields backed by the uploaded universe
file (trading_universe + market_indices). `sync_knowledge_metadata`
soft-joins ICF/IEP when reachable and writes only the fields returned.
"""

from __future__ import annotations

from typing import Any

from institutional_knowledge_tables.store import upsert_fact

_SOURCE_UNIVERSE = "trading_universe+market_indices"


def sync_company_master(ticker: str) -> dict[str, Any]:
    from trading_universe.loader import get_symbol

    t = str(ticker or "").strip().upper()
    base = get_symbol(t)
    if not base:
        return {"ok": False, "ticker": t, "error": "not_in_trading_universe"}

    written: list[str] = []
    facts: dict[str, Any] = {
        "company_id": t,
        "company_name": base.get("name"),
        "ticker": t,
        "isin": base.get("isin") or None,
        "exchange": "NSE",
        "industry": base.get("industry") or None,
        "status": "active" if base.get("tradable") else "inactive",
    }
    for field, value in facts.items():
        if value is None:
            continue  # never write a fabricated placeholder
        upsert_fact(t, "company_master", field, value, source=_SOURCE_UNIVERSE, trigger="universe_sync")
        written.append(field)
    return {"ok": True, "ticker": t, "table": "company_master", "fields_written": written}


def sync_universe_company_master(*, scope: str = "nifty500", limit: int | None = None) -> dict[str, Any]:
    """Onboard every company in the uploaded universe into IKT company_master.

    scope: nifty500 (index books through Nifty 500) | all (full NSE trading book)
    """
    from universe_learning.bootstrap import _scope_symbols

    symbols = _scope_symbols(scope)
    if limit is not None:
        symbols = symbols[: max(0, int(limit))]
    synced = 0
    failed = 0
    for sym in symbols:
        try:
            out = sync_company_master(sym)
            if out.get("ok"):
                synced += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return {
        "ok": True,
        "scope": scope,
        "attempted": len(symbols),
        "synced": synced,
        "failed": failed,
        "message": (
            f"IKT company_master onboarded for {synced}/{len(symbols)} companies "
            f"(scope={scope}) — no code changes required for new listings."
        ),
    }


def sync_knowledge_metadata(ticker: str) -> dict[str, Any]:
    """Soft-join ICF / evidence signals into knowledge_metadata. Writes only
    fields the backend actually returned — never invents a confidence score.
    """
    t = str(ticker or "").strip().upper()
    written: list[str] = []
    try:
        from institutional_coverage_factory.production import icc_status_for

        icc = icc_status_for(t) or {}
        if not icc.get("ok", True) and "status" not in icc:
            raise RuntimeError(icc.get("error") or "icf_unavailable")
        candidates = {
            "institutional_coverage": icc.get("institutional_coverage_complete"),
            "knowledge_confidence": icc.get("knowledge_confidence"),
            "research_ready": icc.get("research_readiness_score"),
            "claim_safe": icc.get("claim_safe"),
        }
        for field, value in candidates.items():
            if value is None:
                continue
            upsert_fact(
                t,
                "knowledge_metadata",
                field,
                value,
                source="institutional_coverage_factory",
                trigger="icf_sync",
            )
            written.append(field)
        return {"ok": True, "ticker": t, "table": "knowledge_metadata", "fields_written": written}
    except Exception as exc:
        return {"ok": False, "ticker": t, "error": str(exc)[:200], "fields_written": written}


__all__ = ["sync_company_master", "sync_knowledge_metadata", "sync_universe_company_master"]
