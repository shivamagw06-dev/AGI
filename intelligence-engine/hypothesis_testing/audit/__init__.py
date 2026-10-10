"""Audit helpers — coverage against institutional quality minima."""

from __future__ import annotations

from typing import Any

from hypothesis_testing.schema import (
    MIN_CONTRADICTORY_EVIDENCE,
    MIN_HISTORICAL_EVIDENCE,
    MIN_MACRO_EVIDENCE,
    MIN_PEER_EVIDENCE,
    MIN_SUPPORTING_EVIDENCE,
)


def _count_kind(evidence: list[dict[str, Any]], *kinds: str) -> int:
    kinds_l = {k.lower() for k in kinds}
    n = 0
    for e in evidence:
        kind = str(e.get("kind") or "").lower()
        text = str(e.get("text") or "").lower()
        if kind in kinds_l:
            n += 1
        elif any(k in text for k in kinds_l):
            n += 1
    return n


def coverage_audit(
    *,
    support_count: int,
    contradiction_count: int,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    historical = _count_kind(evidence, "historical")
    peer = _count_kind(evidence, "peer")
    macro = _count_kind(evidence, "macro")
    checks = {
        "min_supporting": support_count >= MIN_SUPPORTING_EVIDENCE,
        "min_contradictory": contradiction_count >= MIN_CONTRADICTORY_EVIDENCE,
        "min_historical": historical >= MIN_HISTORICAL_EVIDENCE,
        "min_peer": peer >= MIN_PEER_EVIDENCE,
        "min_macro": macro >= MIN_MACRO_EVIDENCE,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "counts": {
            "supporting": support_count,
            "contradictory": contradiction_count,
            "historical": historical,
            "peer": peer,
            "macro": macro,
        },
        "targets": {
            "supporting": MIN_SUPPORTING_EVIDENCE,
            "contradictory": MIN_CONTRADICTORY_EVIDENCE,
            "historical": MIN_HISTORICAL_EVIDENCE,
            "peer": MIN_PEER_EVIDENCE,
            "macro": MIN_MACRO_EVIDENCE,
        },
    }
