"""IEL adapter — Phase 1 Golden Test Set as an evaluation universe suite."""

from __future__ import annotations

from typing import Any

from knowledge_factory.phase1_golden_test_set import (
    PHASE1_GOLDEN_200,
    PHASE1_GOLDEN_ROWS,
    PHASE1_VERSION,
    by_bucket,
    summary,
    validate_universe,
)


def load_universe() -> list[dict[str, Any]]:
    return [dict(r) for r in PHASE1_GOLDEN_ROWS]


def universe_tickers() -> tuple[str, ...]:
    return PHASE1_GOLDEN_200


def universe_board() -> dict[str, Any]:
    v = validate_universe()
    s = summary()
    return {
        "suite": "phase1_golden_200",
        "version": PHASE1_VERSION,
        "valid": v.get("valid"),
        "summary": s,
        "validation": v,
        "buckets": {k: [r["ticker"] for r in rows] for k, rows in by_bucket().items()},
        "n": len(PHASE1_GOLDEN_ROWS),
    }
