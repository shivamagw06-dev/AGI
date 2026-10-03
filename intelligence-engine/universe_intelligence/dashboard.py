"""Universe Health — operational heartbeat every morning."""

from __future__ import annotations

from typing import Any

from universe_intelligence import store as iui_store
from universe_intelligence.ici import ici_leaderboard, institutional_coverage_index
from universe_intelligence.registry import current_members, list_universes, universe_tree
from universe_intelligence.schema import IUI_VERSION, INSTITUTIONAL_COVERAGE_LEVEL, envelope


def universe_health(*, universe_id: str = "NIFTY_500", ensure: bool = True) -> dict[str, Any]:
    """
    Every morning:

        Universe Health
          Coverage · Failures · Stale · Missing · New · Removed · Decision Ready
    """
    uid = universe_id.upper()
    if ensure and not iui_store.list_companies():
        from universe_intelligence.pipeline import run_universe_intelligence_pipeline

        run_universe_intelligence_pipeline(universe_id=uid, force_full=True)

    members = current_members(uid)
    companies = []
    institutional = 0
    decision_ready = 0
    failures = []
    stale = []
    missing = []
    ici_sum = 0.0
    level_hist = {i: 0 for i in range(8)}

    for t in members:
        co = iui_store.get_company(t)
        if not co:
            missing.append(t)
            continue
        companies.append(co)
        level = int(co.get("coverage_level") or 0)
        level_hist[level] = level_hist.get(level, 0) + 1
        ici_sum += float(co.get("ici") or 0)
        if co.get("institutional_coverage"):
            institutional += 1
        if level >= INSTITUTIONAL_COVERAGE_LEVEL:
            decision_ready += 1
        gates = co.get("quality_gates") or {}
        fails = [g for g, v in gates.items() if v == "FAIL"]
        if fails:
            failures.append({"ticker": t, "failed_gates": fails, "ici": co.get("ici")})
        if not co.get("institutional_coverage") or float(co.get("ici") or 0) < 80:
            stale.append(t)

    last_inc = iui_store.get_report("last_incremental") or {}
    payload = last_inc.get("changeset") or last_inc
    # changeset may be nested under incremental payload
    if "changeset" in (last_inc or {}):
        cs = last_inc["changeset"]
    else:
        cs = (last_inc.get("incremental") or {}).get("changeset") or {}

    n = len(members) or 1
    avg_ici = round(ici_sum / max(len(companies), 1), 2)
    board = list_universes()
    tree = universe_tree()
    leaders = ici_leaderboard(members, top=10) if companies else {"top": [], "avg_ici": 0.0}

    health = envelope(
        kind="universe_health",
        payload={
            "title": "AGIB Universe Health",
            "programme": "AGIB v1.2 – Institutional Universe Intelligence",
            "universe_id": uid,
            "north_star": {
                "name": "Institutional Coverage Index",
                "metric": "avg_ici",
                "value": avg_ici,
                "institutional_coverage_n": institutional,
                "universe_n": len(members),
                "institutional_coverage_pct": round(100.0 * institutional / n, 2),
            },
            "coverage": {
                "members": len(members),
                "registry_companies": len(companies),
                "institutional_coverage": institutional,
                "institutional_coverage_pct": round(100.0 * institutional / n, 2),
                "decision_ready": decision_ready,
                "decision_ready_pct": round(100.0 * decision_ready / n, 2),
                "avg_ici": avg_ici,
                "by_level": level_hist,
            },
            "failures": failures[:50],
            "failure_count": len(failures),
            "stale": stale[:50],
            "stale_count": len(stale),
            "missing": missing[:50],
            "missing_count": len(missing),
            "new": list(cs.get("new") or [])[:50],
            "removed": list(cs.get("removed") or [])[:50],
            "changed": list(cs.get("changed") or [])[:50],
            "ici_leaders": leaders.get("top") or [],
            "universes_registered": board.get("n"),
            "universe_tree": tree.get("children"),
            "validation_failures": 0,
            "iui_version": IUI_VERSION,
            "architecture": {
                "stack": [
                    "Universe Registry",
                    "Universe Membership Engine",
                    "Company Registry",
                    "Knowledge Factory",
                    "Evidence Factory",
                    "Existing Institutional Reasoning",
                ],
                "frozen": ["phases_1_7", "knowledge_factory_architecture", "decision_quality"],
            },
        },
    )
    iui_store.put_report("universe_health", health)
    return health


def company_ici_card(ticker: str) -> dict[str, Any]:
    return institutional_coverage_index(ticker)
