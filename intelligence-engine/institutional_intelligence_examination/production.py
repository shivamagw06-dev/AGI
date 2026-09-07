"""IIEX production facade."""

from __future__ import annotations

from typing import Any

from institutional_intelligence_examination.questions import all_questions, section_totals, total_marks
from institutional_intelligence_examination.reports import build_grades, build_markdown, write_docs
from institutional_intelligence_examination.runner import run_exam
from institutional_intelligence_examination.schema import (
    FREEZE_LOCKS,
    IIEX_VERSION,
    MODULE_CODE,
    NO_IIEX_ACTIONS,
    NORMALIZED_PASS,
    NORMALIZED_TOTAL,
    PASS_PCT,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    RESOURCES,
)
from institutional_intelligence_examination.store import STORE


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ok": True,
        "programme": PROGRAMME,
        "programme_short": PROGRAMME_SHORT,
        "module_code": MODULE_CODE,
        "version": IIEX_VERSION,
        "principle": PRIMARY_PRINCIPLE,
        "questions": len(all_questions()),
        "total_marks_bank": total_marks(),
        "normalized_total": NORMALIZED_TOTAL,
        "pass_marks": NORMALIZED_PASS,
        "pass_pct": PASS_PCT,
        "resources_allowed": list(RESOURCES),
        "does_not": list(NO_IIEX_ACTIONS),
        "freeze_locks": FREEZE_LOCKS,
        "ask_triggers_collection": False,
        "providers_queried_always": [],
        "note": "MODULE_CODE IIEX avoids collision with Investment Intelligence Engine (app/iie)",
    }


def dashboard() -> dict[str, Any]:
    latest = STORE.latest()
    summary = (latest or {}).get("summary") or {}
    return {
        "board": "Institutional Intelligence Examination",
        "programme_short": PROGRAMME_SHORT,
        "version": IIEX_VERSION,
        "principle": PRIMARY_PRINCIPLE,
        "questions": len(all_questions()),
        "section_mark_bank": section_totals(),
        "latest_run_id": (latest or {}).get("run_id"),
        "latest_normalized_500": summary.get("normalized_500"),
        "latest_certification": summary.get("certification"),
        "latest_passed": summary.get("passed"),
        "pass_bar": NORMALIZED_PASS,
        "recent_runs": [
            {
                "run_id": r.get("run_id"),
                "normalized_500": (r.get("summary") or {}).get("normalized_500"),
                "certification": (r.get("summary") or {}).get("certification"),
                "generated_at": r.get("generated_at"),
            }
            for r in STORE.history(limit=10)
        ],
        "providers_queried": [],
        "phase": "IIEX-1.0",
    }


def run(*, question_ids: list[str] | None = None, write_docs_flag: bool = True) -> dict[str, Any]:
    out = run_exam(question_ids=question_ids)
    if write_docs_flag and not question_ids:
        try:
            out["docs_written"] = write_docs(out)
        except Exception as exc:
            out["docs_written"] = {"error": str(exc)[:200]}
    return out


def report(*, run_id: str | None = None) -> dict[str, Any]:
    latest = STORE.latest()
    if run_id:
        latest = next((r for r in STORE.history(limit=50) if r.get("run_id") == run_id), latest)
    if not latest:
        latest = run_exam()
    return {
        "run_id": latest.get("run_id"),
        "summary": latest.get("summary"),
        "grades": build_grades(latest),
        "markdown": build_markdown(latest),
        "providers_queried": [],
    }


def grades(*, run_id: str | None = None) -> dict[str, Any]:
    return report(run_id=run_id)["grades"]


def history(*, limit: int = 20) -> dict[str, Any]:
    rows = STORE.history(limit=limit)
    return {
        "n": len(rows),
        "runs": [
            {
                "run_id": r.get("run_id"),
                "normalized_500": (r.get("summary") or {}).get("normalized_500"),
                "certification": (r.get("summary") or {}).get("certification"),
                "passed": (r.get("summary") or {}).get("passed"),
                "generated_at": r.get("generated_at"),
            }
            for r in rows
        ],
        "providers_queried": [],
    }


def questions() -> dict[str, Any]:
    return {
        "n": len(all_questions()),
        "total_marks_bank": total_marks(),
        "sections": section_totals(),
        "questions": [
            {
                "id": q["id"],
                "section": q["section"],
                "title": q["title"],
                "marks": q["marks"],
                "platforms": q.get("platforms"),
            }
            for q in all_questions()
        ],
        "providers_queried": [],
    }
