"""IB-01 certification / scorecard report."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.schema import (
    AGIB_PLATFORM_VERSION,
    COMPARATORS,
    GUIDING_PRINCIPLE,
    IB_PRODUCT,
    IB_VERSION,
    IB_WORKSTREAM_ID,
    INSTITUTIONAL_GRADE_LABEL,
    PASS_THRESHOLD,
    SECTIONS,
    TOTAL_POINTS,
)
from institutional_grade_benchmark.store import panel_complete

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def build_benchmark_report(sections: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
    by_key = {s["key"]: s for s in sections}
    ordered = []
    total_score = 0.0
    total_max = 0.0
    for code, key, title, max_pts in SECTIONS:
        s = by_key.get(key) or {
            "code": code,
            "key": key,
            "title": title,
            "score": 0.0,
            "max": max_pts,
        }
        ordered.append(s)
        total_score += float(s.get("score") or 0)
        total_max += float(s.get("max") or max_pts)

    total_score = round(min(TOTAL_POINTS, total_score), 2)
    harness_any = any(s.get("harness_estimate") for s in ordered)
    pending_panel = any((s.get("meta") or {}).get("pending_panel") for s in ordered)
    panel_ok = panel_complete()
    meets_threshold = total_score >= PASS_THRESHOLD
    grade_ok = meets_threshold
    # Marketing / external claim requires human blind + productivity panels
    claim_safe = grade_ok and panel_ok and not pending_panel
    if not meets_threshold:
        grade_reason = f"Score {total_score} < {PASS_THRESHOLD}"
    elif not claim_safe:
        grade_reason = (
            "Threshold met — record blind (≥3) + Bloomberg/AGIB productivity panels "
            "before external Institutional Grade claims"
        )
    else:
        grade_reason = "Pass — panel-backed Institutional Grade"

    lines = [
        "AGIB Benchmark",
        "",
    ]
    for s in ordered:
        lines.append(f"{s['title']}")
        lines.append(f"{_fmt(s.get('score'))}/{_fmt(s.get('max'), as_int=True)}")
        lines.append("")
    lines.extend(
        [
            "Overall",
            "",
            f"{_fmt(total_score)}/{TOTAL_POINTS}",
            "",
            INSTITUTIONAL_GRADE_LABEL if grade_ok else "Not yet Institutional Grade",
            "",
            "This is the test that matters",
            "",
            "Your PAT tests prove:",
            "",
            '"The software works."',
            "",
            "IB-01 proves:",
            "",
            '"The investment intelligence is competitive."',
            "",
            "Those are completely different claims.",
        ]
    )

    return {
        "workstream_id": IB_WORKSTREAM_ID,
        "product": IB_PRODUCT,
        "version": IB_VERSION,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "as_of": now_iso(),
        "mode": mode,
        "guiding_principle": GUIDING_PRINCIPLE,
        "comparators": list(COMPARATORS),
        "sections": ordered,
        "total_score": total_score,
        "total_max": TOTAL_POINTS,
        "pass_threshold": PASS_THRESHOLD,
        "meets_threshold": meets_threshold,
        "institutional_grade": grade_ok,
        "provisional": grade_ok and not claim_safe,
        "overall_result": INSTITUTIONAL_GRADE_LABEL if grade_ok else "Not yet Institutional Grade",
        "grade_reason": grade_reason,
        "harness_estimate": harness_any,
        "panel_complete": panel_ok,
        "pending_panel": pending_panel,
        "report_text": "\n".join(lines),
        "scorecard": {s["key"]: {"score": s.get("score"), "max": s.get("max")} for s in ordered},
        "claim_safe": claim_safe,
    }


def _fmt(v: Any, as_int: bool = False) -> str:
    try:
        f = float(v)
        if as_int or f == int(f):
            return str(int(f))
        return f"{f:.0f}" if abs(f - round(f)) < 0.05 else f"{f:.1f}"
    except Exception:  # noqa: BLE001
        return str(v)
