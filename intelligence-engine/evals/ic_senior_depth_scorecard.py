"""Score senior IC depth habits. Evaluation-only. Never trains."""

from __future__ import annotations

import re
from typing import Any

from evals.ic_senior_depth_held_out import NEVER_TRAIN, QUESTIONS, TOTAL_RUBRIC_POINTS
from institutional_reasoning.engine import package_reasoning_answer

assert NEVER_TRAIN is True


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _contains(text: str, needle: str, *, ban: bool = False) -> bool:
    n = needle.lower().strip()
    if not n:
        return True
    if ban and re.fullmatch(r"[a-z]+", n) and len(n) <= 6:
        return re.search(rf"(?<![a-z-]){re.escape(n)}(?![a-z-])", text) is not None
    if re.fullmatch(r"[a-z0-9%]+", n) and len(n) <= 14:
        return re.search(rf"(?<![a-z]){re.escape(n)}[a-z]*", text) is not None
    return n in text


def score_item(item: dict[str, Any], packaged: dict[str, Any]) -> dict[str, Any]:
    text = _norm(packaged.get("executive") or "")
    needles = [n for n in (item.get("must_include") or []) if n]
    needles_ok = all(_contains(text, n) for n in needles) if needles else bool(text)
    banned_ok = not any(_contains(text, b, ban=True) for b in (item.get("must_not_include") or []) if b)
    # soften buy/sell if refusing recommendations
    if not banned_ok and ("do not" in text or "no buy" in text or "recommendation" in text):
        banned_ok = not re.search(r"\b(we\s+)?(buy|sell)\b.{0,15}\b(stock|shares)\b", text)

    count_ok = True
    if item.get("min_questions"):
        count_ok = len(re.findall(r"\(\d+\)", text)) >= int(item["min_questions"])

    mode_ok = packaged.get("mode") == item.get("mode_hint")
    checks = {
        "owns_executive": bool(packaged.get("owns_executive")),
        "needles_ok": needles_ok,
        "banned_ok": banned_ok,
        "mode_ok": mode_ok,
        "structure_ok": len(text.split()) >= 40,
        "count_ok": count_ok,
        "source_ic": packaged.get("source") == "ic_case_study_reasoning",
    }
    passed = all(checks.values())
    marks = int(item["marks"])
    earned = marks if passed else int(marks * sum(1 for v in checks.values() if v) / len(checks))
    return {
        "id": item["id"],
        "passed": passed,
        "marks": marks,
        "earned": earned,
        "checks": checks,
        "mode_got": packaged.get("mode"),
        "executive_preview": (packaged.get("executive") or "")[:240],
    }


def run_senior_depth_scorecard() -> dict[str, Any]:
    rows = []
    for item in QUESTIONS:
        packaged = package_reasoning_answer(item["question"])
        rows.append(score_item(item, packaged))
    earned = sum(r["earned"] for r in rows)
    possible = sum(r["marks"] for r in rows)
    passed_n = sum(1 for r in rows if r["passed"])
    return {
        "ok": True,
        "never_train": True,
        "case_id": "ic_senior_depth_v1",
        "passed": passed_n,
        "total": len(rows),
        "points_earned": earned,
        "points_possible": possible,
        "points_max_design": TOTAL_RUBRIC_POINTS,
        "claim_discipline": (
            f"perfect_on_this_senior_depth_set_{passed_n}_of_{len(rows)}"
            if passed_n == len(rows) and earned == possible
            else f"scored_{earned}_of_{possible}_on_this_senior_depth_set"
        ),
        "results": rows,
    }
