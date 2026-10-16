"""Learning engine — expected → observed → difference → reason → lesson → updated knowledge."""

from __future__ import annotations

from typing import Any

from institutional_memory.mistake_intelligence.engine import classify_mistakes, mistake_summary
from institutional_memory.store.corpus import append_learning, get_company


def generate_lessons(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "lessons": []}
    lessons = list(company.get("lessons") or [])
    # Also synthesize from forecast misses if lesson missing
    synthesized = []
    for f in company.get("forecasts") or []:
        if f.get("actual_outcome") and f.get("learning"):
            synthesized.append(
                {
                    "date": f.get("date"),
                    "expected": f.get("most_likely"),
                    "observed": f.get("actual_outcome"),
                    "difference": f"{f.get('most_likely')} vs {f.get('actual_outcome')}",
                    "reason": "forecast_calibration",
                    "lesson": f.get("learning"),
                    "updated_knowledge": f.get("learning"),
                    "source": "forecast_memory",
                }
            )
    return {
        "found": True,
        "ticker": company["ticker"],
        "lessons": lessons,
        "synthesized_from_forecasts": synthesized,
        "lessons_generated_after_outcomes": len(lessons) >= 1 or len(synthesized) >= 1,
        "rule": "Compare expected vs observed → reason → lesson → updated institutional knowledge",
    }


def learning_summary(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper()}
    lessons = generate_lessons(ticker)
    mistakes = mistake_summary(ticker)
    theses = company.get("theses") or []
    improved = False
    if len(theses) >= 2:
        # crude: later closed theses with correct/partially_correct after earlier miss
        outcomes = [t.get("outcome") for t in theses if t.get("outcome") not in (None, "open")]
        if outcomes:
            improved = outcomes[-1] in {"correct", "partially_correct"}
    what_failed = [m.get("example") or m.get("context") for m in (classify_mistakes(ticker).get("mistakes") or [])]
    what_improved = [l.get("updated_knowledge") or l.get("lesson") for l in (lessons.get("lessons") or [])]
    return {
        "found": True,
        "ticker": company["ticker"],
        "institutional_learning": {
            "what_improved": what_improved,
            "what_failed": what_failed,
            "thinking_improved": improved,
            "lesson_count": len(lessons.get("lessons") or []),
            "mistake_intelligence": mistakes,
        },
        "lessons": lessons.get("lessons"),
        "rule": "Learning is active — memory alone is not enough",
    }


def apply_learning_update(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = payload.get("ticker") or payload.get("company")
    lesson = {
        "date": payload.get("date"),
        "expected": payload.get("expected"),
        "observed": payload.get("observed"),
        "difference": payload.get("difference"),
        "reason": payload.get("reason"),
        "lesson": payload.get("lesson") or payload.get("lessons"),
        "updated_knowledge": payload.get("updated_knowledge") or payload.get("lesson"),
        "mistake": payload.get("mistake"),
    }
    return append_learning(str(ticker or ""), lesson)
