"""Collect Phase 2 evidence + company analysis + decision-engine views for one name."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from committee_certification_v2.schema import IC10_V2_ROWS


def resolve_row(display: str) -> tuple[str, str, str]:
    key = (display or "").upper().replace(".NS", "").replace(".BO", "")
    for disp, resolve, sector in IC10_V2_ROWS:
        if key in {disp, resolve}:
            return disp, resolve, sector
    return key, key, "unknown"


def collect_company(
    display: str,
    *,
    force: bool = False,
    max_peers: int = 4,
    ownership_xbrl: int = 2,
    quarterly_xbrl: int = 4,
    annual_xbrl: int = 2,
) -> dict[str, Any]:
    """Live collect for certification. Fail-open per layer; never fabricates."""
    disp, resolve, sector = resolve_row(display)
    t0 = datetime.now(timezone.utc)
    errors: list[str] = []

    market: dict[str, Any] = {}
    try:
        from live_market_context.production import analyse as market_analyse

        market = market_analyse(resolve, force=force)
    except Exception as exc:  # noqa: BLE001
        market = {"ok": False, "error": str(exc)[:160]}
        errors.append(f"market:{exc}"[:120])

    ownership: dict[str, Any] = {}
    try:
        from ownership_intelligence.production import analyse as ownership_analyse

        ownership = ownership_analyse(resolve, xbrl_quarters=ownership_xbrl, persist=False, force=force)
    except Exception as exc:  # noqa: BLE001
        ownership = {"ok": False, "error": str(exc)[:160]}
        errors.append(f"ownership:{exc}"[:120])

    earnings: dict[str, Any] = {}
    try:
        from earnings_intelligence.production import analyse as earnings_analyse

        earnings = earnings_analyse(
            resolve,
            quarterly_xbrl=quarterly_xbrl,
            annual_xbrl=annual_xbrl,
            persist=False,
            force=force,
        )
    except Exception as exc:  # noqa: BLE001
        earnings = {"ok": False, "error": str(exc)[:160]}
        errors.append(f"earnings:{exc}"[:120])

    valuation: dict[str, Any] = {}
    try:
        from valuation_intelligence.production import analyse as valuation_analyse

        # Prefer display key for peer registry (TATAMOTORS → TMPV peers via alias)
        val_key = disp if disp == "TATAMOTORS" else resolve
        valuation = valuation_analyse(val_key, max_peers=max_peers, persist=False, force=force)
        # If TATAMOTORS not in registry, fall back to TMPV
        if not valuation.get("ok") and disp == "TATAMOTORS":
            valuation = valuation_analyse(resolve, max_peers=max_peers, persist=False, force=force)
    except Exception as exc:  # noqa: BLE001
        valuation = {"ok": False, "error": str(exc)[:160]}
        errors.append(f"valuation:{exc}"[:120])

    # Soft CID dossier
    dossier: dict[str, Any] = {
        "ticker": resolve,
        "identity": {
            "ticker": resolve,
            "sector": sector,
            "sector_id": sector,
            "peers": [],
        },
        "sector_framework": {"sector_id": sector, "sector_name": sector},
    }
    try:
        from ownership_intelligence.enrich import merge_ownership_into_dossier

        if ownership.get("ok"):
            dossier = merge_ownership_into_dossier(dossier, ownership)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cid_own:{exc}"[:120])
    try:
        from earnings_intelligence.enrich import merge_financials_into_dossier

        if earnings.get("ok"):
            dossier = merge_financials_into_dossier(dossier, earnings)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cid_fin:{exc}"[:120])
    try:
        from valuation_intelligence.enrich import merge_valuation_into_dossier

        if valuation.get("ok"):
            dossier = merge_valuation_into_dossier(dossier, valuation)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cid_val:{exc}"[:120])

    # Market soft-fill
    if market.get("ok") or market.get("ltp") is not None:
        md = dict(dossier.get("market_data") or {})
        md["current_price"] = market.get("ltp") or md.get("current_price")
        md["provider"] = market.get("provider")
        md["as_of"] = market.get("as_of")
        md["live_market_context"] = {
            "ok": bool(market.get("ok") or market.get("ltp") is not None),
            "provider": market.get("provider"),
            "ltp": market.get("ltp"),
        }
        dossier["market_data"] = md

    company_analysis: dict[str, Any] = {}
    try:
        from company_analysis.production import analyse as ca_analyse

        company_analysis = ca_analyse(
            f"Committee certification for {disp}",
            ticker=resolve,
            cid=dossier,
        )
    except Exception as exc:  # noqa: BLE001
        company_analysis = {"enabled": False, "error": str(exc)[:160]}
        errors.append(f"ca:{exc}"[:120])

    decision: dict[str, Any] = {}
    try:
        from decision_engine.production import package_for_ask_agi as de_package

        decision = de_package(
            query=f"Can I buy {disp} today? Long-term thesis, risks, catalysts, gate status.",
            ticker=resolve,
            company_analysis=company_analysis,
            cid=dossier,
        )
    except Exception as exc:  # noqa: BLE001
        decision = {"enabled": False, "error": str(exc)[:160]}
        errors.append(f"de:{exc}"[:120])

    latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    return {
        "display": disp,
        "resolve": resolve,
        "sector_key": sector,
        "market": market,
        "ownership": ownership,
        "earnings": earnings,
        "valuation": valuation,
        "cid": dossier,
        "company_analysis": company_analysis,
        "decision": decision,
        "errors": errors,
        "latency_ms": latency_ms,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def collect_universe(**kwargs: Any) -> dict[str, Any]:
    rows = []
    for disp, _, _ in IC10_V2_ROWS:
        rows.append(collect_company(disp, **kwargs))
    return {
        "n": len(rows),
        "rows": rows,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
