"""Benchmark Center soft-slice for Mission Control."""

from __future__ import annotations

from typing import Any, Optional


def benchmark_center_board(report: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    r = dict(report or {})
    sections = r.get("sections") or []
    return {
        "benchmark_center": True,
        "status": (
            "institutional_grade"
            if r.get("institutional_grade")
            else ("ok" if r else "idle")
        ),
        "total_score": r.get("total_score"),
        "total_max": r.get("total_max") or 1000,
        "pass_threshold": r.get("pass_threshold") or 900,
        "institutional_grade": bool(r.get("institutional_grade")),
        "provisional": bool(r.get("provisional")),
        "claim_safe": bool(r.get("claim_safe")),
        "overall_result": r.get("overall_result") or "NOT RUN",
        "panel_complete": bool(r.get("panel_complete")),
        "section_scores": [
            {
                "code": s.get("code"),
                "title": s.get("title"),
                "score": s.get("score"),
                "max": s.get("max"),
            }
            for s in sections
        ],
        "mission": (
            "Can AGIB produce institutional-grade research comparable to "
            "Bloomberg, Capital IQ, FactSet, AlphaSense, and sell-side?"
        ),
        "distinct_from_pat": (
            "PAT proves the software works. IB-01 proves the investment "
            "intelligence is competitive."
        ),
    }
