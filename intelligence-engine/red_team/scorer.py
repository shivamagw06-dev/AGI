"""Score Red Team answers blindly collected from the engine."""

from __future__ import annotations

import re
from typing import Any

from red_team.bank import RED_TEAM_BANK
from red_team.blind_runner import run_blind_item, run_blind_suite
from red_team.ecr import compute_ecr
from red_team.failure_db import append_failure, build_failure_record, summarise_failures
from red_team.rules import CAPABILITY_GATE_RULE, RED_TEAM_RULES


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _has(text: str, needle: str) -> bool:
    n = needle.lower().strip()
    if not n:
        return True
    # Accept any of several alternatives separated by '|'
    if "|" in n:
        return any(_has(text, part.strip()) for part in n.split("|") if part.strip())
    if re.fullmatch(r"[a-z0-9\-]+", n) and len(n) <= 12:
        return re.search(rf"(?<![a-z]){re.escape(n)}[a-z]*", text) is not None
    return n in text


def score_blind_result(item: dict[str, Any], blind: dict[str, Any]) -> dict[str, Any]:
    packaged = blind.get("packaged") or {}
    text = _norm(packaged.get("executive") or "")
    owns = bool(packaged.get("owns_executive") and text)
    needles = [n for n in (item.get("must_include") or []) if n]
    # For must_include with multiple tokens that are alternatives conceptually,
    # require all listed needles (AND). Use soft stems.
    soft_needles_ok = True
    for n in needles:
        if n in {"non-recurring", "one-off"}:
            if not (_has(text, "non-recurring") or _has(text, "one-off") or _has(text, "one-time") or _has(text, "disposal")):
                soft_needles_ok = False
        elif n == "not enough":
            if not (_has(text, "not enough") or _has(text, "isn't enough") or _has(text, "is not enough") or _has(text, "cannot")):
                soft_needles_ok = False
        elif n == "not necessarily":
            if not (_has(text, "not necessarily") or _has(text, "does not establish") or _has(text, "doesn't establish")):
                soft_needles_ok = False
        elif n == "should not":
            if not (_has(text, "should not") or _has(text, "no.") or text.startswith("no ")):
                soft_needles_ok = False
        elif n == "not acceptable":
            if not (_has(text, "not acceptable") or _has(text, "should not") or _has(text, "must be refused") or _has(text, "refuse")):
                soft_needles_ok = False
        elif n == "old price":
            if not (_has(text, "old price") or _has(text, "old print") or _has(text, "historical") or _has(text, "prior")):
                soft_needles_ok = False
        elif n == "one quarter":
            if not (_has(text, "one quarter") or _has(text, "single quarter") or _has(text, "one beat")):
                soft_needles_ok = False
        elif n in {"asset sale", "factory", "plant", "disposal"}:
            if not any(_has(text, x) for x in ("asset sale", "factory", "plant", "disposal", "disposals")):
                soft_needles_ok = False
        elif n == "alone":
            if not (_has(text, "alone") or _has(text, "single") or _has(text, "one quarter")):
                soft_needles_ok = False
        else:
            if not _has(text, n):
                soft_needles_ok = False

    banned = item.get("must_not_include") or []
    banned_ok = True
    for b in banned:
        bl = (b or "").lower().strip()
        if not bl:
            continue
        # Affirmative failure slogans only.
        affirmative_hits = (
            f"yes, {bl}" in text
            or f"yes {bl}" in text
            or text.startswith(bl)
            or f"clearly {bl}" in text
        )
        if affirmative_hits:
            banned_ok = False
            break
        # Exact risky claims that appear without negation nearby.
        if bl in text:
            idx = text.find(bl)
            window = text[max(0, idx - 24) : idx + len(bl) + 8]
            if any(n in window for n in ("not ", "n't", "no ", "cannot", "shouldn't", "should not")):
                continue
            if bl in {
                "impossible",
                "data must be wrong",
                "justified by the beat alone",
                "yes, the business is clearly improving",
                "company a is better",
                "company b is better",
            }:
                banned_ok = False
                break

    ecr = packaged.get("ecr") or compute_ecr(
        conclusion=str(packaged.get("direct_answer") or ""),
        answer_text=text,
    )

    checks = {
        "owns_executive": owns,
        "needles_ok": soft_needles_ok,
        "banned_ok": banned_ok,
        "engine_blind_to_category": blind.get("engine_saw_category") is False,
        "ecr_attached": "ecr" in packaged or ecr.get("ecr") is not None,
    }
    passed = all(checks.values())
    return {
        "id": item.get("id"),
        "category": item.get("category"),
        "passed": passed,
        "checks": checks,
        "detected_family": packaged.get("family_id"),
        "detected_mode": packaged.get("mode"),
        "source": packaged.get("source"),
        "habit_id": packaged.get("habit_id"),
        "consistency_fingerprint": packaged.get("consistency_fingerprint"),
        "ecr": ecr,
        "executive_preview": (packaged.get("executive") or "")[:240],
        "expected_behaviors": item.get("expected_behaviors") or [],
    }


def run_red_team_scorecard(
    *,
    persist_failures: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    items = list(RED_TEAM_BANK)
    if limit is not None:
        items = items[:limit]
    rows: list[dict[str, Any]] = []
    failures_logged = 0

    for item in items:
        blind = run_blind_item(item)
        row = score_blind_result(item, blind)
        rows.append(row)
        if not row["passed"] and persist_failures:
            hints = item.get("failure_hints") or {}
            record = build_failure_record(
                test_id=item.get("id"),
                question=item["question"],
                expected_category=item.get("category"),
                detected_family=row.get("detected_family"),
                detected_mode=row.get("detected_mode"),
                evidence_used=list((row.get("ecr") or {}).get("supported_by") or []),
                evidence_missed=list(hints.get("evidence_missed", "").split("; "))
                if hints.get("evidence_missed")
                else [],
                reasoning_mistake=hints.get("reasoning_mistake"),
                editorial_mistake=None,
                root_cause="red_team_rubric_miss",
                fix="Investigate bias-defense / evidence process; do not train on this prompt text.",
                ecr=row.get("ecr"),
                answer_preview=row.get("executive_preview"),
                extra={"failed_checks": [k for k, v in row["checks"].items() if not v]},
            )
            append_failure(record)
            failures_logged += 1

    # Consistency group: one_off_profit paraphrases should share habit fingerprint.
    group = [r for r in rows if r.get("category") == "internal_consistency"]
    fps = {r.get("consistency_fingerprint") for r in group if r.get("consistency_fingerprint")}
    habits = {r.get("habit_id") for r in group if r.get("habit_id")}
    consistency_ok = len(group) >= 3 and len(fps) == 1 and len(habits) == 1
    if group:
        for r in rows:
            if r.get("category") == "internal_consistency":
                r["checks"]["consistency_group_ok"] = consistency_ok
                r["passed"] = r["passed"] and consistency_ok

    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    score = round(100.0 * passed / total, 2) if total else 0.0
    by_cat: dict[str, dict[str, int]] = {}
    for item, row in zip(items, rows):
        cat = str(item.get("category"))
        bucket = by_cat.setdefault(cat, {"pass": 0, "total": 0})
        bucket["total"] += 1
        if row["passed"]:
            bucket["pass"] += 1

    return {
        "lab": "AGIB Red Team",
        "never_train": True,
        "engine_blind_to_categories": True,
        "rules": list(RED_TEAM_RULES),
        "capability_gate_rule": CAPABILITY_GATE_RULE,
        "total": total,
        "passed": passed,
        "score_per_100": score,
        "interpretation": (
            "perfect_on_this_red_team_set"
            if score >= 99.9
            else "strong_on_this_red_team_set"
            if score >= 80
            else "mixed_on_this_red_team_set"
            if score >= 50
            else "weak_on_this_red_team_set"
        ),
        "caution": (
            "A Red Team score measures this hidden set only. Continuously refresh prompts. "
            "Do not equate a high score with overfitting-proof genuine reasoning."
        ),
        "consistency_group_ok": consistency_ok,
        "failures_logged": failures_logged,
        "failure_db": summarise_failures(),
        "by_category": by_cat,
        "failures": [r for r in rows if not r["passed"]],
        "rows": rows,
    }
