"""Score Phase-2 held-out generalisation questions.

Never trains. Never mutates gold patterns.
"""

from __future__ import annotations

import re
from typing import Any

from evals.reasoning_phase2_held_out import EVAL_BANK, NEVER_TRAIN
from institutional_reasoning.engine import package_reasoning_answer


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _contains_phrase(text: str, needle: str, *, ban: bool = False) -> bool:
    n = needle.lower().strip()
    if not n:
        return True
    if ban and re.fullmatch(r"[a-z]+", n) and len(n) <= 6:
        # Avoid matching selling/sell-through/buyer when banning sell/buy.
        return re.search(rf"(?<![a-z-]){re.escape(n)}(?![a-z-])", text) is not None
    if re.fullmatch(r"[a-z]+", n) and len(n) <= 8:
        # Positive needles allow simple stems ("yield" matches "yields", "differ"→"differs").
        return re.search(rf"(?<![a-z]){re.escape(n)}[a-z]*", text) is not None
    return n in text


def score_item(item: dict[str, Any], packaged: dict[str, Any]) -> dict[str, Any]:
    text = _norm(packaged.get("executive") or "")
    expected = item.get("family")
    got = packaged.get("family_id")

    if packaged.get("owns_executive") and got == expected:
        family_ok = True
    elif packaged.get("owns_executive") and expected == "dual_hypothesis":
        family_ok = got == "dual_hypothesis"
    elif packaged.get("owns_executive") and expected in {"contradiction", "accounting"} and got in {
        "contradiction",
        "accounting",
    }:
        family_ok = True
    elif packaged.get("owns_executive") and expected in {"evidence", "valuation"} and got in {
        "evidence",
        "valuation",
    }:
        family_ok = True
    elif packaged.get("owns_executive") and expected in {"evidence", "valuation"} and got == "contradiction":
        family_ok = item.get("generated_variant") is True
    # Allow causality ↔ contradiction adjacency for macro-with-conflict prompts.
    elif packaged.get("owns_executive") and expected in {"causality", "contradiction"} and got in {
        "causality",
        "contradiction",
    }:
        family_ok = True
    elif packaged.get("owns_executive") and expected in {
        "uncertainty",
        "self_critique",
        "comparison",
    } and got in {
        "uncertainty",
        "self_critique",
        "comparison",
        "contradiction",
        "accounting",
    }:
        family_ok = expected == got or item.get("generated_variant") is True
    else:
        family_ok = bool(packaged.get("owns_executive") and got == expected)

    needles = [n for n in (item.get("must_include") or []) if n]
    needles_ok = all(_contains_phrase(text, n) for n in needles) if needles else bool(text)
    banned = item.get("must_not_include") or []
    banned_ok = not any(_contains_phrase(text, b, ban=True) for b in banned if b)
    structure_ok = bool(text) and len(text.split()) >= 35
    novelty = packaged.get("novelty") or {}
    no_force = novelty.get("force_closest_template") is False
    decision_ok = True
    if item.get("forbids_decision"):
        decision_ok = (
            packaged.get("decides_winner") is False
            or "do not decide" in text
            or "do not pick" in text
            or "hold both" in text
        )
        if any(p in text for p in ("the correct explanation is", "therefore the answer is")):
            decision_ok = False

    # Exact gold reuse is fine when it is the same family habit.
    # Penalise only when a gold template is forced onto a different family.
    overfit_ok = True
    if novelty.get("band") == "seen_exact" and expected and got and expected != got:
        if not (
            expected in {"contradiction", "accounting"}
            and got in {"contradiction", "accounting"}
        ) and not (
            expected in {"evidence", "valuation"} and got in {"evidence", "valuation"}
        ):
            overfit_ok = False

    checks = {
        "owns_executive": bool(packaged.get("owns_executive")),
        "family_ok": family_ok,
        "needles_ok": needles_ok,
        "banned_ok": banned_ok,
        "structure_ok": structure_ok,
        "no_force_template": no_force,
        "decision_ok": decision_ok,
        "family_not_overridden_badly": overfit_ok,
    }
    passed = all(checks.values())
    return {
        "id": item.get("id"),
        "family_expected": expected,
        "family_got": got,
        "passed": passed,
        "checks": checks,
        "novelty": novelty,
        "answer_policy": packaged.get("answer_policy"),
        "executive_preview": (packaged.get("executive") or "")[:220],
    }


def run_scorecard(limit: int | None = None) -> dict[str, Any]:
    assert NEVER_TRAIN is True
    items = list(EVAL_BANK)
    if limit is not None:
        items = items[:limit]
    rows = []
    for item in items:
        packaged = package_reasoning_answer(item["question"])
        rows.append(score_item(item, packaged))
    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    by_family: dict[str, dict[str, int]] = {}
    for item, row in zip(items, rows):
        fam = str(item.get("family"))
        bucket = by_family.setdefault(fam, {"pass": 0, "total": 0})
        bucket["total"] += 1
        if row["passed"]:
            bucket["pass"] += 1
    score = round(100.0 * passed / total, 2) if total else 0.0
    band = (
        "perfect_on_this_held_out_set"
        if score >= 99.9
        else "strong_on_this_held_out_set"
        if score >= 90
        else "mixed_on_this_held_out_set"
        if score >= 70
        else "weak_on_this_held_out_set"
    )
    return {
        "evaluation_only": True,
        "never_train": True,
        "total": total,
        "passed": passed,
        "score_per_100": score,
        "benchmark_band": band,
        # Legacy key kept for compatibility; do not read as a claim of unbounded reasoning.
        "legacy_band_alias": band,
        "interpretation_caution": (
            "A perfect score demonstrates success on this held-out set only — "
            "not proof of genuine reasoning in general."
        ),
        "by_family": by_family,
        "failures": [r for r in rows if not r["passed"]],
        "rows": rows,
    }


__all__ = ["run_scorecard", "score_item"]
