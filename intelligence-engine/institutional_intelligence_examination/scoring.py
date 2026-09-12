"""Deterministic CIO-grade scoring — no LLM grading."""

from __future__ import annotations

from typing import Any

from institutional_intelligence_examination.schema import EVAL_DIMENSIONS, NORMALIZED_TOTAL, PASS_PCT


def _section_present(answer: dict[str, Any], key: str) -> bool:
    sections = answer.get("sections") or {}
    if key in sections and sections[key] not in (None, "", [], {}):
        return True
    if key in answer and answer[key] not in (None, "", [], {}):
        return True
    return False


def score_answer(q: dict[str, Any], answer: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    required = list(q.get("required_sections") or [])
    present = sum(1 for s in required if _section_present(answer, s))
    coverage = present / max(1, len(required))

    evidence = answer.get("supporting_evidence") or (answer.get("sections") or {}).get("supporting_evidence") or []
    evidence_n = len(evidence) if isinstance(evidence, list) else 0
    sources = pack.get("sources") or []
    evidence_score = min(1.0, 0.35 + 0.08 * evidence_n + 0.06 * len(sources))

    # Integration across platforms
    platforms_hit = len(set(sources))
    integration = min(1.0, 0.4 + 0.1 * platforms_hit)

    # Guardrails
    no_internet = answer.get("internet_used") is False and pack.get("internet_used") is False
    no_providers = (answer.get("providers_queried") or []) == [] and (pack.get("providers_queried") or []) == []
    guard = 1.0 if (no_internet and no_providers) else 0.5

    # CIO depth heuristics
    depth = 0.55
    blob = str(answer)
    for token in (
        "Bull",
        "Base",
        "Bear",
        "analogue",
        "confidence",
        "probability",
        "transmission",
        "invalidat",
        "historical",
        "relationship",
    ):
        if token.lower() in blob.lower():
            depth += 0.05
    depth = min(1.0, depth)

    # Scenario / multi-path bonus for forecast-like questions
    multi_path = 1.0
    if any(k in (q.get("dimensions") or []) for k in ("forecasting",)):
        has_bbb = "Bull" in blob and "Base" in blob and "Bear" in blob
        multi_path = 1.0 if has_bbb else 0.75

    quality = (
        0.34 * coverage
        + 0.22 * evidence_score
        + 0.16 * integration
        + 0.12 * depth
        + 0.10 * guard
        + 0.06 * multi_path
    )
    marks_available = int(q["marks"])
    marks_awarded = round(marks_available * quality, 2)
    # Floor: incomplete required sections hard-cap
    if coverage < 0.5:
        marks_awarded = min(marks_awarded, marks_available * 0.45)
    if not no_internet or not no_providers:
        marks_awarded = min(marks_awarded, marks_available * 0.4)

    return {
        "question_id": q["id"],
        "marks_available": marks_available,
        "marks_awarded": marks_awarded,
        "pct": round(100.0 * marks_awarded / marks_available, 2),
        "coverage_pct": round(100.0 * coverage, 2),
        "evidence_n": evidence_n,
        "sources": sources,
        "platforms_hit": platforms_hit,
        "quality": round(quality, 4),
        "guardrails": {"no_internet": no_internet, "no_providers": no_providers},
        "required_present": present,
        "required_total": len(required),
        "dimensions": list(q.get("dimensions") or []),
    }


def aggregate_scores(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available = sum(r["marks_available"] for r in rows)
    awarded = sum(r["marks_awarded"] for r in rows)
    pct = 100.0 * awarded / max(1, available)
    normalized = round(NORMALIZED_TOTAL * awarded / max(1, available), 2)
    passed = pct >= PASS_PCT

    # Dimension scores (normalized to EVAL_DIMENSIONS totals)
    dim_marks: dict[str, list[float]] = {k: [] for k in EVAL_DIMENSIONS}
    for r in rows:
        for d in r.get("dimensions") or []:
            if d in dim_marks:
                dim_marks[d].append(r["pct"])
    dimension_scores = {}
    for d, weight in EVAL_DIMENSIONS.items():
        vals = dim_marks.get(d) or []
        avg = sum(vals) / len(vals) if vals else pct
        dimension_scores[d] = {
            "weight": weight,
            "avg_pct": round(avg, 2),
            "marks": round(weight * avg / 100.0, 2),
        }
    dim_total = round(sum(v["marks"] for v in dimension_scores.values()), 2)

    return {
        "marks_available": available,
        "marks_awarded": round(awarded, 2),
        "pct": round(pct, 2),
        "normalized_500": normalized,
        "pass_pct_required": PASS_PCT,
        "normalized_pass_required": 450,
        "passed": passed,
        "certification": (
            "INSTITUTIONAL READY"
            if normalized >= 450
            else ("PARTIALLY READY" if normalized >= 375 else "NOT READY")
        ),
        "dimension_scores": dimension_scores,
        "dimension_total_500": dim_total,
    }
