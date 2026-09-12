"""Orion IC Case Study V2 scorecard (500 points).

Evaluation-only. Never trains. Never mutates matchers.
Claim discipline: scores are on this set only.
"""

from __future__ import annotations

import re
from typing import Any

from evals.orion_ic_case_study_v2_held_out import (
    CASE_FACTS,
    CASE_ID,
    NEVER_TRAIN,
    QUESTIONS,
    RUBRIC_AREAS,
    TOTAL_RUBRIC_POINTS,
)
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
    if re.fullmatch(r"[a-z]+", n) and len(n) <= 12:
        return re.search(rf"(?<![a-z]){re.escape(n)}[a-z]*", text) is not None
    return n in text


def build_prompt(item: dict[str, Any]) -> str:
    return (
        f"{CASE_FACTS}\n\n"
        f"INSTITUTIONAL CASE QUESTION ({item['id']}):\n"
        f"{item['question']}\n"
        f"Answer with CFA-level institutional investment-committee reasoning. "
        f"Detect hidden traps. No directional stock recommendation labels."
    )


def score_item(item: dict[str, Any], packaged: dict[str, Any]) -> dict[str, Any]:
    text = _norm(packaged.get("executive") or "")
    words = len(text.split()) if text else 0
    needles = [n for n in (item.get("must_include") or []) if n]
    needles_ok = all(_contains(text, n) for n in needles) if needles else bool(text)
    banned = item.get("must_not_include") or []
    banned_ok = True
    for b in banned:
        if not b:
            continue
        if b.lower() in {"buy", "sell", "hold"} and (
            "cannot conclude" in text
            or "no directional" in text
            or "recommendation" in text
            or "do not" in text
            or "not warrant" in text
        ):
            if re.search(rf"\b(we\s+)?{b.lower()}\b.{{0,20}}\b(orion|stock|shares)\b", text):
                banned_ok = False
                break
            continue
        if _contains(text, b, ban=True):
            banned_ok = False
            break

    structure_ok = words >= 50
    owns = bool(packaged.get("owns_executive"))
    hint = item.get("mode_hint")
    mode_ok = True
    if hint and packaged.get("source") == "ic_case_study_reasoning":
        mode_ok = packaged.get("mode") == hint
    elif hint:
        mode_ok = needles_ok and owns

    uncertainty_ok = any(
        p in text
        for p in (
            "uncertainty",
            "missing",
            "cannot",
            "confidence",
            "monitor",
            "pending",
            "additional evidence",
            "alternative",
            "scenario",
            "trade-off",
            "do not",
        )
    )
    checks = {
        "owns_executive": owns,
        "needles_ok": needles_ok,
        "banned_ok": banned_ok,
        "structure_ok": structure_ok,
        "mode_ok": mode_ok,
        "no_forced_decision": packaged.get("decides_winner") is False
        or packaged.get("forbids_buy_sell_hold") is True,
        "uncertainty_signal": uncertainty_ok,
    }
    passed = all(checks.values())
    marks = int(item.get("marks") or 0)
    passed_n = sum(1 for v in checks.values() if v)
    earned = marks if passed else int(marks * passed_n / len(checks))
    return {
        "id": item.get("id"),
        "section": item.get("section"),
        "areas": item.get("areas") or [],
        "marks": marks,
        "earned": earned,
        "passed": passed,
        "checks": checks,
        "mode_got": packaged.get("mode"),
        "source": packaged.get("source"),
        "words": words,
        "executive_preview": (packaged.get("executive") or "")[:280],
    }


def run_orion_v2_scorecard(*, limit: int | None = None) -> dict[str, Any]:
    items = QUESTIONS[: int(limit)] if limit else list(QUESTIONS)
    rows: list[dict[str, Any]] = []
    for item in items:
        packaged = package_reasoning_answer(
            build_prompt(item),
            company="Orion Global Industries",
        )
        rows.append(score_item(item, packaged))

    total_earned = sum(int(r["earned"]) for r in rows)
    total_possible = sum(int(r["marks"]) for r in rows)
    area_earned = {k: 0.0 for k in RUBRIC_AREAS}
    area_possible = {k: 0.0 for k in RUBRIC_AREAS}
    for item, row in zip(items, rows):
        areas = item.get("areas") or []
        if not areas:
            continue
        share_m = float(item["marks"]) / len(areas)
        share_e = float(row["earned"]) / len(areas)
        for a in areas:
            if a in area_possible:
                area_possible[a] += share_m
                area_earned[a] += share_e

    passed_n = sum(1 for r in rows if r["passed"])
    claim = (
        f"perfect_on_this_orion_v2_set_{passed_n}_of_{len(rows)}"
        if passed_n == len(rows) and total_earned == total_possible
        else f"scored_{total_earned}_of_{total_possible}_on_this_orion_v2_set"
    )
    return {
        "ok": True,
        "case_id": CASE_ID,
        "never_train": True,
        "evaluation_only": True,
        "claim_discipline": claim,
        "passed": passed_n,
        "total": len(rows),
        "points_earned": total_earned,
        "points_possible": total_possible,
        "points_max_design": TOTAL_RUBRIC_POINTS,
        "score_pct": round(100.0 * total_earned / max(total_possible, 1), 1),
        "area_scores": {
            k: {"earned": round(area_earned[k], 1), "possible": round(area_possible[k], 1)}
            for k in RUBRIC_AREAS
        },
        "results": rows,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_orion_v2_scorecard(), indent=2)[:12000])
