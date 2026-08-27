"""P2.3 Ownership Intelligence — production façade (standard engine contract)."""

from __future__ import annotations

from typing import Any

from ownership_intelligence.pack import build_ownership_pack
from ownership_intelligence.schema import (
    ENGINE_CODE,
    ENGINE_NAME,
    FRESHNESS_SLA_DAYS,
    MILESTONE,
    PROGRAMME,
    RUNTIME_BUDGET_S,
    VERSION,
    WORKSTREAM_ID,
)
from ownership_intelligence.store import persist_pack

try:
    from phase2_investment_intelligence.contract import build_engine_contract
except Exception:  # pragma: no cover
    build_engine_contract = None  # type: ignore


def health() -> dict[str, Any]:
    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {}
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "contract": contract,
        "runtime_budget_s": RUNTIME_BUDGET_S,
        "freshness_sla_days": FRESHNESS_SLA_DAYS,
        "extends_intelligence": True,
        "replaces_baseline": False,
        "sources": ["nse_master", "nse_xbrl"],
        "implementation_pr_checklist": [
            "What intelligence did we add?",
            "What measurable metric improved?",
            "What metric stayed unchanged?",
            "Did IAT still pass?",
            "Did UNKNOWN drift remain zero?",
        ],
    }


def analyse(
    ticker: str,
    *,
    force: bool = False,
    xbrl_quarters: int = 4,
    persist: bool = True,
    skip_xbrl: bool = False,
    injected_master: list[dict[str, Any]] | None = None,
    injected_xbrl_by_period: dict[str, bytes | str] | None = None,
) -> dict[str, Any]:
    """Ownership intelligence pack for one ticker."""
    pack = build_ownership_pack(
        ticker,
        force=force,
        xbrl_quarters=xbrl_quarters,
        skip_xbrl=skip_xbrl,
        injected_master=injected_master,
        injected_xbrl_by_period=injected_xbrl_by_period,
    )
    store_result = None
    if persist and pack.get("ok") and injected_master is None:
        try:
            store_result = persist_pack(pack)
        except Exception as exc:  # noqa: BLE001
            store_result = {"error": str(exc)[:160]}

    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {"engine": ENGINE_CODE}
    intel = pack.get("intelligence") or {}
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "contract": contract,
        "ticker": pack.get("ticker"),
        "ok": pack.get("ok"),
        "detail_ok": pack.get("detail_ok"),
        "score": pack.get("score"),
        "ownership_quality": intel.get("ownership_quality"),
        "evidence": pack.get("evidence") or [],
        "confidence": pack.get("confidence"),
        "freshness": pack.get("freshness") or {},
        "lineage": pack.get("lineage") or [],
        "ownership": pack.get("ownership"),
        "promoter": pack.get("promoter"),
        "fii": pack.get("fii"),
        "dii": pack.get("dii"),
        "mutual_funds": pack.get("mutual_funds"),
        "insurance": pack.get("insurance"),
        "public": pack.get("public"),
        "promoter_pledge": pack.get("promoter_pledge"),
        "promoter_pledge_pct": pack.get("promoter_pledge_pct"),
        "as_of_quarter": pack.get("as_of_quarter"),
        "quarter_history": pack.get("quarter_history"),
        "qoq": pack.get("qoq"),
        "intelligence": intel,
        "source": pack.get("source"),
        "store": store_result,
        "degraded": not pack.get("ok"),
        "degraded_reason": (pack.get("errors") or [None])[0] if not pack.get("ok") else None,
        "failure_mode": {
            "strategy": "degrade_gracefully",
            "block_unrelated_engines": False,
            "fabricated": False,
        },
        "fabricated": False,
        "baseline_compatible": True,
        "missing": pack.get("missing"),
        "generated_at": pack.get("generated_at"),
        "latency_ms": pack.get("latency_ms"),
        "errors": pack.get("errors") or [],
    }


def package_for_ask_agi(
    query: str = "",
    *,
    ticker: str | None = None,
    force: bool = False,
    xbrl_quarters: int = 2,
    **_: Any,
) -> dict[str, Any]:
    """Soft Ask AGI entry — degrade if no ticker."""
    t = (ticker or "").upper().strip() or None
    if not t:
        # Only accept explicit equity-style tokens; ignore English words in the query.
        import re

        _STOP = {
            "WHAT",
            "IS",
            "THE",
            "FOR",
            "AND",
            "OWNERSHIP",
            "SHAREHOLDING",
            "PROMOTER",
            "SHOULD",
            "BUY",
            "THIS",
            "COMPANY",
            "ABOUT",
            "WITH",
            "FROM",
            "HAVE",
            "HAS",
            "ARE",
            "WAS",
            "HOW",
            "WHY",
            "WHO",
            "WHEN",
            "WHERE",
            "PLEASE",
            "TELL",
            "GIVE",
            "SHOW",
        }
        for m in re.finditer(r"\b([A-Z]{2,15})\b", (query or "").upper()):
            tok = m.group(1)
            if tok not in _STOP and not tok.isdigit():
                t = tok
                break
    if not t:
        return {
            "enabled": True,
            "engine": ENGINE_CODE,
            "skipped": True,
            "reason": "no_ticker",
            "failure_mode": {
                "strategy": "degrade_gracefully",
                "block_unrelated_engines": False,
                "fabricated": False,
            },
            "baseline_compatible": True,
            "fabricated": False,
        }
    return analyse(t, force=force, xbrl_quarters=xbrl_quarters, persist=False)


def attach_to_cid(ticker: str, dossier: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Build ownership pack and merge into CID dossier."""
    from ownership_intelligence.enrich import merge_ownership_into_dossier

    pack = analyse(ticker, persist=False, **kwargs)
    base = dossier if isinstance(dossier, dict) else {"ticker": ticker.upper()}
    merged = merge_ownership_into_dossier(base, pack if pack.get("ok") else {})
    return {"dossier": merged, "pack": pack, "attached": bool(pack.get("ok"))}
