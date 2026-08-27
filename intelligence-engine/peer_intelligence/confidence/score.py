"""PIL confidence — coverage of peer universe, history depth, source quality."""

from __future__ import annotations

from typing import Any

from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker


def score_comparison(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    if not pack:
        return {
            "confidence": 20.0,
            "breakdown": {"peer_coverage": 0, "history_depth": 0, "source_quality": 20, "completeness": 0},
            "explain": "No peer pack resolved",
            "missing_data": ["peer_pack"],
        }

    series = [s for s in pack.get("series") or [] if s.get("entity") == t]
    depths = [len(s.get("points") or {}) for s in series]
    avg_depth = sum(depths) / len(depths) if depths else 0
    direct_n = len(pack.get("direct_universe") or [])
    metrics_covered = len({s.get("metric") for s in series})

    mixed = sum(1 for s in series if s.get("data_class") in {"mixed", "filing"})
    seed = sum(1 for s in series if s.get("data_class") == "seed_panel")
    source_quality = 55.0 + min(35.0, 10.0 * mixed) - min(20.0, 2.0 * seed)

    peer_coverage = min(100.0, direct_n * 18.0)
    history_depth = min(100.0, avg_depth * 16.0)
    completeness = min(100.0, metrics_covered * 12.0) - min(30.0, 8.0 * len(pack.get("missing") or []))
    completeness = max(0.0, completeness)

    # weights
    conf = round(
        peer_coverage * 0.30 + history_depth * 0.25 + source_quality * 0.25 + completeness * 0.20,
        1,
    )
    return {
        "confidence": conf,
        "breakdown": {
            "peer_coverage": round(peer_coverage, 1),
            "history_depth": round(history_depth, 1),
            "source_quality": round(source_quality, 1),
            "completeness": round(completeness, 1),
        },
        "weights": {
            "peer_coverage": 0.30,
            "history_depth": 0.25,
            "source_quality": 0.25,
            "completeness": 0.20,
        },
        "explain": (
            f"Peer coverage {peer_coverage:.0f}×30% + History {history_depth:.0f}×25% + "
            f"Source {source_quality:.0f}×25% + Completeness {completeness:.0f}×20% = {conf:.0f}"
        ),
        "missing_data": pack.get("missing") or [],
        "data_class_note": "Seed panels reduce source_quality until filings automation completes.",
    }
