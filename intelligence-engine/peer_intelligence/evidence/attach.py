"""Attach ComparisonEvidence objects to PIL outputs (EIL-compatible)."""

from __future__ import annotations

from typing import Any

from peer_intelligence.benchmarking.engine import benchmarks_for
from peer_intelligence.confidence.score import score_comparison
from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker
from peer_intelligence.schema import ComparisonEvidence


def evidence_bundle(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    bench = benchmarks_for(t)
    conf = score_comparison(t)
    if not pack:
        return {"ticker": t, "evidence": [], "confidence": conf}

    universe = pack.get("direct_universe") or []
    rows = []
    for c in bench.get("comparisons") or []:
        ev = ComparisonEvidence(
            metric=c["metric"],
            source=c.get("source") or "seed_panel",
            period="panel_latest",
            peer_universe=list(universe),
            confidence=conf["confidence"],
            missing_data=list(pack.get("missing") or []),
        )
        rows.append(ev.to_dict())
    return {
        "ticker": t,
        "evidence": rows,
        "confidence": conf,
        "rule": "Every comparison must cite source, period, peer universe, metric, confidence, missing data",
    }
