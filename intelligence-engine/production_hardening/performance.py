"""Performance profiling — graph, replay, research generation timings."""

from __future__ import annotations

from typing import Any

from production_hardening.schema import GOLD_REGRESSION_UNIVERSE
from production_hardening.util import now_iso, rss_mb, timed


def run_performance_profile(
    *,
    tickers: list[str] | tuple[str, ...] | None = None,
    injected_by_ticker: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    universe = list(tickers) if tickers else list(GOLD_REGRESSION_UNIVERSE)
    profiles = []
    rss0 = rss_mb()

    for t in universe:
        inj = (injected_by_ticker or {}).get(t)
        row: dict[str, Any] = {"ticker": t}

        # Collect / memory path
        pack, ms_collect = timed(_collect, t) if not inj else (inj, 0.0)
        row["collect_ms"] = ms_collect
        mem = pack.get("memory") if isinstance(pack.get("memory"), dict) else None

        # Graph traversal
        graph, ms_graph = timed(_graph, t, mem)
        row["graph_ms"] = ms_graph
        row["graph_nodes"] = (graph or {}).get("n_nodes")
        row["graph_edges"] = (graph or {}).get("n_edges")

        # Opportunity (research prioritisation)
        oie, ms_oie = timed(_oie, t, mem, graph if isinstance(graph, dict) else None)
        row["opportunity_ms"] = ms_oie

        # Decision replay reconstruction
        replay, ms_replay = timed(_replay, t, pack if isinstance(pack, dict) else None)
        row["replay_ms"] = ms_replay
        row["replay_reproducible"] = (replay or {}).get("reproducible")

        # Research generation
        draft, ms_research = timed(_research, pack if isinstance(pack, dict) else {"ok": False})
        row["research_generate_ms"] = ms_research
        row["research_ok"] = (draft or {}).get("ok")

        row["total_ms"] = round(
            sum(
                float(row.get(k) or 0)
                for k in ("collect_ms", "graph_ms", "opportunity_ms", "replay_ms", "research_generate_ms")
            ),
            2,
        )
        profiles.append(row)

    profiles_sorted = sorted(profiles, key=lambda r: -(r.get("total_ms") or 0))
    return {
        "as_of": now_iso(),
        "n": len(profiles),
        "rss_mb_start": rss0,
        "rss_mb_end": rss_mb(),
        "profiles": profiles,
        "slowest": profiles_sorted[:5],
        "avg_ms": {
            "collect": _avg(profiles, "collect_ms"),
            "graph": _avg(profiles, "graph_ms"),
            "opportunity": _avg(profiles, "opportunity_ms"),
            "replay": _avg(profiles, "replay_ms"),
            "research_generate": _avg(profiles, "research_generate_ms"),
            "total": _avg(profiles, "total_ms"),
        },
        "notes": [
            "Profiles compiled-intelligence paths only (no raw API fan-out by default).",
            "Use scale_test for multi-thousand universe throughput.",
        ],
        "recommendation_policy": "hardening_diagnostics_only_no_buy_sell",
    }


def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def _collect(ticker: str) -> dict[str, Any]:
    from investment_operations.collect import collect_company

    return collect_company(ticker, persist_memory=False, include_soft_reasoning=False)


def _graph(ticker: str, memory: dict[str, Any] | None) -> dict[str, Any]:
    from investment_knowledge_graph.build import build_company_graph

    return build_company_graph(ticker, memory=memory)


def _oie(ticker: str, memory: dict[str, Any] | None, graph: dict[str, Any] | None) -> dict[str, Any]:
    from opportunity_intelligence.production import analyse

    if memory and memory.get("ok"):
        return analyse(
            ticker,
            injected_memory=memory,
            injected_graph=graph,
            compile_if_missing=False,
            persist_memory=False,
        )
    return analyse(ticker, persist_memory=False)


def _replay(ticker: str, pack: dict[str, Any] | None) -> dict[str, Any]:
    from investment_operations.replay import build_decision_replay

    return build_decision_replay(ticker, company_pack=pack)


def _research(pack: dict[str, Any]) -> dict[str, Any]:
    from autonomous_research.generator import generate_research_pack

    return generate_research_pack(pack)
