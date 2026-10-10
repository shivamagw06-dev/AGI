"""Three-tier reasoning evaluation.

Tiers
-----
1. Gold Patterns — known habits still work
2. Hidden Generalisation — Phase-2 held-out (related but unseen)
3. Adversarial Chaos — Phase 3–8 (never train)

Important: a perfect score on any one tier is evidence about THAT tier only.
It is not by itself a claim of unbounded genuine reasoning.
"""

from __future__ import annotations

import re
from typing import Any

from evals.adversarial_chaos_held_out import ADVERSARIAL_BANK, ADVERSARIAL_CORE, NEVER_TRAIN as ADV_NEVER
from evals.phase2_scorecard import run_scorecard as run_phase2_scorecard
from evals.phase2_scorecard import score_item as score_phase2_item
from institutional_reasoning.engine import package_reasoning_answer
from institutional_reasoning.gold_patterns import package_pattern_answer


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _has(text: str, needle: str) -> bool:
    n = needle.lower().strip()
    if not n:
        return True
    if re.fullmatch(r"[a-z]+", n) and len(n) <= 8:
        return re.search(rf"(?<![a-z]){re.escape(n)}[a-z]*", text) is not None
    return n in text


GOLD_SMOKE = [
    (
        "t1_profit_vs_roe",
        "HDFC Bank's net profit increased 12%, but Return on Equity (ROE) declined. "
        "Which metric deserves more attention, and why?",
    ),
    (
        "t2_revenue_vs_operating_margin",
        "Revenue increased 25%, but operating margin declined. Is this positive or negative?",
    ),
    (
        "t4_news_without_filing",
        "A news article says Infosys won a large contract, but there is no NSE filing yet. "
        "How should AIG treat this?",
    ),
]


def score_gold_tier() -> dict[str, Any]:
    rows = []
    for pattern_id, question in GOLD_SMOKE:
        gold = package_pattern_answer(question)
        packaged = package_reasoning_answer(question)
        ok = (
            gold.get("enabled") is True
            and gold.get("pattern_id") == pattern_id
            and packaged.get("owns_executive") is True
        )
        rows.append(
            {
                "id": pattern_id,
                "passed": ok,
                "source": packaged.get("source"),
                "pattern_id": packaged.get("pattern_id") or gold.get("pattern_id"),
            }
        )
    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    return {
        "tier": "gold_patterns",
        "purpose": "Verify known reasoning habits still work",
        "never_train_claim": False,
        "total": total,
        "passed": passed,
        "score_per_100": round(100.0 * passed / total, 2) if total else 0.0,
        "interpretation": "habit_regression_check",
        "rows": rows,
    }


def score_hidden_generalisation_tier() -> dict[str, Any]:
    # Reuse Phase-2 scorecard; reinterpret band language.
    raw = run_phase2_scorecard()
    score = raw["score_per_100"]
    return {
        "tier": "hidden_generalisation",
        "purpose": "Measure performance on unseen but related questions",
        "never_train": True,
        "total": raw["total"],
        "passed": raw["passed"],
        "score_per_100": score,
        "interpretation": (
            "perfect_on_this_held_out_set"
            if score >= 99.9
            else "strong_on_this_held_out_set"
            if score >= 90
            else "mixed_on_this_held_out_set"
            if score >= 70
            else "weak_on_this_held_out_set"
        ),
        "caution": (
            "A high score shows success on this held-out generalisation set. "
            "It does not by itself prove unbounded genuine reasoning."
        ),
        "by_family": raw.get("by_family"),
        "failures": raw.get("failures"),
    }


def score_adversarial_item(item: dict[str, Any], packaged: dict[str, Any]) -> dict[str, Any]:
    text = _norm(packaged.get("executive") or "")
    mode_ok = packaged.get("mode") == item.get("mode") or (
        packaged.get("source") == "adversarial_unknown_reasoning"
        and packaged.get("habit_id")
    )
    owns = bool(packaged.get("owns_executive") and text)
    needles = [n for n in (item.get("must_include") or []) if n]
    needles_ok = all(_has(text, n) for n in needles) if needles else owns
    banned = item.get("must_not_include") or []
    banned_ok = not any(_has(text, b) for b in banned if b)
    novelty = packaged.get("novelty") or {}
    no_force = novelty.get("force_closest_template") is False

    special_ok = True
    if item.get("forbids_decision"):
        special_ok = packaged.get("decides_winner") is False and (
            "do not decide" in text or "hold both" in text or "competing" in text
        )
    if item.get("require_decomposition"):
        special_ok = special_ok and (
            "airline" in text and ("bank" in text) and ("decompos" in text or "separately" in text or "map" in text)
        )
    if item.get("require_hierarchy"):
        special_ok = special_ok and ("filing" in text) and ("social" in text)
    if item.get("require_evidence_boundary"):
        special_ok = special_ok and ("cannot" in text) and ("cash" in text)
    if item.get("require_separation"):
        special_ok = special_ok and ("separate" in text) and ("valuation" in text)
    if item.get("require_no_forced_single_trend"):
        special_ok = special_ok and ("neither" in text or "both" in text or "depends" in text or "horizons" in text)
    if item.get("require_no_real_company_recall"):
        special_ok = special_ok and not any(x in text for x in ("hdfc", "infosys", "reliance", "tcs"))

    checks = {
        "owns_executive": owns,
        "mode_ok": bool(mode_ok),
        "needles_ok": needles_ok,
        "banned_ok": banned_ok,
        "no_force_template": no_force,
        "special_ok": special_ok,
        "high_novelty": float(novelty.get("novelty_score") or 0) >= 0.5,
    }
    return {
        "id": item.get("id"),
        "phase": item.get("phase"),
        "mode_expected": item.get("mode"),
        "mode_got": packaged.get("mode"),
        "passed": all(checks.values()),
        "checks": checks,
        "habit_id": packaged.get("habit_id"),
        "consistency_fingerprint": packaged.get("consistency_fingerprint"),
        "executive_preview": (packaged.get("executive") or "")[:220],
    }


def score_adversarial_tier(*, core_only: bool = False) -> dict[str, Any]:
    assert ADV_NEVER is True
    items = list(ADVERSARIAL_CORE if core_only else ADVERSARIAL_BANK)
    rows = [score_adversarial_item(item, package_reasoning_answer(item["question"])) for item in items]

    # Phase-8 consistency: same habit fingerprint across paraphrases.
    cons = [r for r in rows if str(r.get("id", "")).startswith("A10")]
    fingerprints = {r.get("consistency_fingerprint") for r in cons if r.get("consistency_fingerprint")}
    habits = {r.get("habit_id") for r in cons if r.get("habit_id")}
    consistency_ok = len(cons) >= 3 and len(fingerprints) == 1 and len(habits) == 1
    if cons:
        for r in rows:
            if str(r.get("id", "")).startswith("A10"):
                r["checks"]["consistency_group_ok"] = consistency_ok
                r["passed"] = r["passed"] and consistency_ok

    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    score = round(100.0 * passed / total, 2) if total else 0.0
    return {
        "tier": "adversarial_chaos",
        "purpose": "Combine multiple families, incomplete evidence and conflicting signals",
        "never_train": True,
        "total": total,
        "passed": passed,
        "score_per_100": score,
        "consistency_group_ok": consistency_ok,
        "interpretation": (
            "perfect_on_this_adversarial_set"
            if score >= 99.9
            else "strong_on_this_adversarial_set"
            if score >= 85
            else "mixed_on_this_adversarial_set"
            if score >= 60
            else "weak_on_this_adversarial_set"
        ),
        "caution": (
            "Success here is necessary but not sufficient for claiming transferable institutional "
            "reasoning. Re-test after code changes and with newly written adversarial prompts."
        ),
        "failures": [r for r in rows if not r["passed"]],
        "rows": rows,
    }


def run_three_tier_scorecard() -> dict[str, Any]:
    gold = score_gold_tier()
    hidden = score_hidden_generalisation_tier()
    adversarial = score_adversarial_tier()
    return {
        "benchmarks": {
            "gold_patterns": gold,
            "hidden_generalisation": hidden,
            "adversarial_chaos": adversarial,
        },
        "summary": {
            "gold_score_per_100": gold["score_per_100"],
            "hidden_generalisation_score_per_100": hidden["score_per_100"],
            "adversarial_chaos_score_per_100": adversarial["score_per_100"],
        },
        "claim_discipline": (
            "Do not equate a perfect held-out score with proven genuine reasoning in general. "
            "Require adversarial success, stability after changes, cross-sector robustness, "
            "and low hallucination under incomplete evidence."
        ),
        "never_train_tiers": ["hidden_generalisation", "adversarial_chaos"],
    }


__all__ = [
    "run_three_tier_scorecard",
    "score_adversarial_item",
    "score_adversarial_tier",
    "score_gold_tier",
    "score_hidden_generalisation_tier",
]
