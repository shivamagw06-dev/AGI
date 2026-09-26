"""Extract structured failures from an IEL suite summary."""

from __future__ import annotations

from typing import Any

from root_cause_intelligence.failures.models import build_failure

# Dimension misses that matter even when overall question still "passes"
_ACTIONABLE_DIMS = ("framework", "intent", "playbook", "replay", "hallucinated_evidence", "unsupported_claims")


def extract_failures(
    scored_rows: list[dict[str, Any]],
    *,
    include_dimension_misses: bool = True,
) -> list[dict[str, Any]]:
    """
    Hard failures (passed=False) always included.

    When include_dimension_misses=True, also include questions that passed overall
    but failed framework/intent/(critical) dimensions — these drive Sprint 3.3/3.4.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in scored_rows or []:
        qid = str(row.get("question_id") or "")
        if not row.get("passed"):
            f = build_failure(row)
            f["failure_class"] = "hard"
            out.append(f)
            seen.add(qid)
            continue
        if not include_dimension_misses:
            continue
        dims = row.get("dimensions") or {}
        soft_causes = []
        for dim in _ACTIONABLE_DIMS:
            j = dims.get(dim) or {}
            if j.get("passed") is False and j.get("root_cause"):
                soft_causes.append(str(j["root_cause"]))
        if not soft_causes:
            continue
        # Rebuild row with soft causes as primary for clustering
        soft_row = dict(row)
        soft_row["root_causes"] = soft_causes
        soft_row["passed"] = False  # treat as actionable for RCI
        soft_row["verdict"] = soft_row.get("verdict") or "PARTIAL"
        f = build_failure(soft_row)
        f["failure_class"] = "dimension_miss"
        f["overall_passed"] = True
        if qid not in seen:
            out.append(f)
            seen.add(qid)
    return out
