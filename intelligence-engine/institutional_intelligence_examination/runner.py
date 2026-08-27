"""IIEX exam runner — CIO Investment Committee Assessment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from institutional_intelligence_examination.answer import answer_question
from institutional_intelligence_examination.probe import gather_for_question
from institutional_intelligence_examination.questions import all_questions, section_totals, total_marks
from institutional_intelligence_examination.schema import (
    IIEX_VERSION,
    MODULE_CODE,
    NORMALIZED_TOTAL,
    PASS_PCT,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    RESOURCES,
)
from institutional_intelligence_examination.scoring import aggregate_scores, score_answer
from institutional_intelligence_examination.store import STORE


def run_exam(*, question_ids: list[str] | None = None) -> dict[str, Any]:
    questions = all_questions()
    if question_ids:
        allow = set(question_ids)
        questions = [q for q in questions if q["id"] in allow]

    results = []
    for q in questions:
        pack = gather_for_question(q)
        answer = answer_question(q, pack)
        scored = score_answer(q, answer, pack)
        results.append(
            {
                "question": {
                    "id": q["id"],
                    "section": q["section"],
                    "title": q["title"],
                    "marks": q["marks"],
                    "prompt": q["prompt"],
                },
                "answer": answer,
                "evidence_pack": {
                    "sources": pack.get("sources"),
                    "providers_queried": [],
                    "internet_used": False,
                    "evidence_n": pack.get("evidence_n"),
                },
                "score": scored,
            }
        )

    summary = aggregate_scores([r["score"] for r in results])
    by_section: dict[str, dict[str, Any]] = {}
    for r in results:
        sec = r["question"]["section"]
        bucket = by_section.setdefault(sec, {"available": 0.0, "awarded": 0.0, "n": 0})
        bucket["available"] += r["score"]["marks_available"]
        bucket["awarded"] += r["score"]["marks_awarded"]
        bucket["n"] += 1
    for sec, b in by_section.items():
        b["pct"] = round(100.0 * b["awarded"] / max(1, b["available"]), 2)

    run = {
        "run_id": f"iiex_{uuid4().hex[:12]}",
        "programme": PROGRAMME,
        "programme_short": PROGRAMME_SHORT,
        "module_code": MODULE_CODE,
        "version": IIEX_VERSION,
        "principle": PRIMARY_PRINCIPLE,
        "resources_allowed": list(RESOURCES),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(results),
        "total_marks_bank": total_marks(),
        "section_mark_bank": section_totals(),
        "summary": {**summary, "by_section": by_section},
        "results": results,
        "normalized_total": NORMALIZED_TOTAL,
        "pass_pct": PASS_PCT,
        "providers_queried": [],
        "internet_used": False,
        "negative_marks": False,
    }
    STORE.save(run)
    return run
