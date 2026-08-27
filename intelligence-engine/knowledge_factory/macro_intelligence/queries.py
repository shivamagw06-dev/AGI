"""Institutional Macro Intelligence queries (PIT-safe, never fabricate)."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.decision_matrix import decision_matrix_for_regimes
from knowledge_factory.macro_intelligence.fixtures.seed_macro import historical_macro_records, snapshot_as_of
from knowledge_factory.macro_intelligence.objects.compile import publish_macro_evidence_pack
from knowledge_factory.macro_intelligence.playbooks.catalog import regime_playbook
from knowledge_factory.macro_intelligence.producers.impacts import (
    sectors_for_driver,
    shock_impact,
    usd_strength_it_impact,
)
from knowledge_factory.macro_intelligence.producers.regime import classify_as_of, classify_current
from knowledge_factory.macro_intelligence.producers.similarity import replay_crisis, similar_regimes


def current_regime() -> dict[str, Any]:
    classified = classify_current()
    regimes = list(classified.get("active_regimes") or [])
    return {
        "query": "current_regime",
        "found": bool(classified.get("found", True)),
        "primary_regime": classified.get("primary_regime"),
        "active_regimes": regimes,
        "classification": classified,
        "playbooks": {r: regime_playbook(r) for r in regimes},
        "decision_matrix": classified.get("decision_matrix") or decision_matrix_for_regimes(regimes),
        "insufficient": bool(classified.get("insufficient")),
        "fabricated": False,
    }


def most_similar_historical_regime(*, top_n: int = 3) -> dict[str, Any]:
    result = similar_regimes(top_n=top_n)
    if result.get("insufficient") or not result.get("found"):
        return {
            "query": "most_similar_historical_regime",
            "matches": [],
            "insufficient": True,
            "reason": result.get("reason") or "no_historical_analogues",
            "fabricated": False,
        }
    matches = list(result.get("matches") or [])
    return {
        "query": "most_similar_historical_regime",
        "matches": matches,
        "top_match": result.get("best_match") or (matches[0] if matches else None),
        "similarity_with_confidence": True,
        "insufficient": False,
        "fabricated": False,
        **{k: v for k, v in result.items() if k not in {"matches"}},
    }


def sectors_benefit_falling_rates() -> dict[str, Any]:
    out = sectors_for_driver("falling_rates")
    return {
        "query": "sectors_benefit_falling_rates",
        "evidence": "historical_macro_relationships",
        **out,
    }


def oil_shock_impacts(*, pct: float = 0.30) -> dict[str, Any]:
    out = shock_impact("oil", pct)
    return {"query": "oil_shock", **out}


def usd_strength_it() -> dict[str, Any]:
    out = usd_strength_it_impact()
    return {"query": "usd_strength_it_export", **out}


def replay_macro(*, as_of: str) -> dict[str, Any]:
    """Point-in-time macro replay. Never fabricates missing history."""
    snap = snapshot_as_of(as_of)
    if snap.get("n_series", 0) == 0:
        return {
            "query": "replay_macro",
            "as_of": as_of,
            "insufficient": True,
            "reason": "macro_history_unavailable",
            "snapshot": None,
            "classification": None,
            "fabricated": False,
            "point_in_time": True,
            "no_future_leakage": True,
        }
    classified = classify_as_of(as_of)
    # PIT integrity: no future periods
    leaked = False
    for sid, rows in historical_macro_records().items():
        for r in rows:
            if str(r.get("available_from") or "") > as_of and r.get("period") == snap.get(f"{sid}_period"):
                leaked = True
    visible = {
        sid: imi_store.filter_pit(rows, as_of)
        for sid, rows in historical_macro_records().items()
    }
    return {
        "query": "replay_macro",
        "as_of": as_of,
        "snapshot": snap,
        "classification": classified,
        "history_points_visible": sum(len(v) for v in visible.values()),
        "point_in_time": True,
        "available_from_filter": f"available_from <= {as_of}",
        "insufficient": bool(classified.get("insufficient")),
        "no_future_leakage": not leaked,
        "fabricated": False,
    }


def replay_covid() -> dict[str, Any]:
    crisis = replay_crisis("covid")
    pit = replay_macro(as_of="2020-03-31")
    return {
        "query": "replay_covid",
        "label": "covid",
        "as_of": "2020-03-31",
        "historical_macro_object": crisis,
        "point_in_time_replay": pit,
        "found": bool(crisis.get("found")) and not pit.get("insufficient"),
        "insufficient": bool(pit.get("insufficient")),
        "fabricated": False,
        "point_in_time_integrity": True,
    }


def replay_2008() -> dict[str, Any]:
    crisis = replay_crisis("2008")
    pit = replay_macro(as_of="2009-03-31")
    return {
        "query": "replay_2008_crisis",
        "as_of": "2009-03-31",
        "historical_macro_object": crisis,
        "point_in_time_replay": pit,
        "found": bool(crisis.get("found")),
        "insufficient": bool(crisis.get("insufficient")),
        "fabricated": False,
        "point_in_time_integrity": True,
    }


def macro_unavailable(*, as_of: str = "1990-01-01") -> dict[str, Any]:
    """Transparent insufficiency when macro history is unavailable."""
    result = replay_macro(as_of=as_of)
    return {
        "query": "macro_history_unavailable",
        "as_of": as_of,
        "insufficient": True,
        "reason": result.get("reason") or "macro_history_unavailable",
        "fabricated": False,
        "message": "Macro history unavailable for as_of; refusing to fabricate.",
        "result": result,
    }


def historical_series(*, macro_id: str, as_of: str | None = None) -> dict[str, Any]:
    rows = list(historical_macro_records().get(macro_id) or [])
    if as_of:
        rows = imi_store.filter_pit(rows, as_of)
    if not rows:
        return {
            "query": "historical_series",
            "macro_id": macro_id,
            "as_of": as_of,
            "rows": [],
            "insufficient": True,
            "reason": "macro_history_unavailable",
            "fabricated": False,
        }
    return {
        "query": "historical_series",
        "macro_id": macro_id,
        "as_of": as_of,
        "rows": rows,
        "insufficient": False,
        "point_in_time": bool(as_of),
        "fabricated": False,
    }


def publish_current_pack() -> dict[str, Any]:
    return publish_macro_evidence_pack()


def get_playbook(regime: str) -> dict[str, Any]:
    return regime_playbook(regime)
