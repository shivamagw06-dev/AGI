"""P5.9 Institutional Workspace — unified company page aggregating existing engines."""

from __future__ import annotations

from typing import Any

from investment_operations.replay import build_decision_replay
from investment_operations.util import now_iso, resolve_ticker


def build_workspace(
    ticker: str,
    *,
    company_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from investment_operations.collect import collect_company

    pack = company_pack or collect_company(ticker, include_soft_reasoning=True, persist_memory=False)
    entity = pack.get("entity") or resolve_ticker(ticker)
    oie = pack.get("opportunity") or {}
    mem = pack.get("memory") or {}
    graph = pack.get("knowledge_graph") or {}
    replay = build_decision_replay(entity, company_pack=pack)

    return {
        "entity": entity,
        "display": pack.get("display") or entity,
        "as_of": now_iso(),
        "ok": bool(pack.get("ok")),
        "modules": {
            "company_memory": {
                "present": bool(mem.get("ok")),
                "memory_version": mem.get("memory_version"),
                "coverage": mem.get("coverage"),
                "compiled_at": mem.get("compiled_at"),
                "sections": {
                    "financial_history": bool(mem.get("financial_history")),
                    "ownership_history": bool(mem.get("ownership_history")),
                    "valuation_history": bool(mem.get("valuation_history")),
                    "corporate_history": bool(mem.get("corporate_history")),
                    "event_timeline": bool(mem.get("event_timeline")),
                },
            },
            "knowledge_delta": mem.get("memory_delta") or pack.get("memory_delta") or (
                (oie.get("opportunity") or {}).get("knowledge_delta") if isinstance(oie.get("opportunity"), dict) else None
            ),
            "knowledge_graph": {
                "present": bool(graph.get("n_nodes")),
                "n_nodes": graph.get("n_nodes"),
                "n_edges": graph.get("n_edges"),
                "peers": graph.get("peers"),
                "themes": graph.get("themes"),
                "sector_key": graph.get("sector_key"),
            },
            "opportunity_pack": {
                "present": bool(oie.get("ok")),
                "score": oie.get("score"),
                "research_priority": oie.get("research_priority"),
                "why_now": oie.get("why_now"),
                "catalysts": oie.get("catalysts") or [],
                "blockers": oie.get("blockers") or [],
                "strengths": oie.get("strengths") or [],
            },
            "scenarios": {
                "present": bool((pack.get("scenarios") or {}).get("_ok")),
                "pack": _thin_soft(pack.get("scenarios")),
            },
            "hypotheses": {
                "present": bool((pack.get("hypotheses") or {}).get("_ok")),
                "pack": _thin_soft(pack.get("hypotheses")),
            },
            "contradictions": {
                "present": bool((pack.get("contradictions") or {}).get("_ok")),
                "pack": _thin_soft(pack.get("contradictions")),
            },
            "catalysts": oie.get("catalysts") or [],
            "committee_view": {
                "present": False,
                "note": "Soft-consume investment_committee / ICR via Ask path when opinions available",
            },
            "decision_replay": replay,
        },
        "unified": True,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
    }


def _thin_soft(pack: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(pack, dict):
        return None
    return {
        k: pack.get(k)
        for k in ("enabled", "status", "version", "engine", "ticker", "entity", "error", "_ok", "_soft")
        if k in pack
    }
