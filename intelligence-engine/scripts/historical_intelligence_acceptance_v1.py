#!/usr/bin/env python3
"""Phase 7.2 acceptance — Historical Intelligence Engine.

250 historical questions across every module, generated over the companies the
warehouse actually holds.

The pass rule is the one that matters: **a correctly coverage-limited answer
counts as correct.** An engine that says "I hold price-to-book only from May
2023" when that is the truth has answered well. An engine that says "cheapest
ever" from the same data has failed, even though every number it printed was
real. So the suite checks for honesty violations rather than for confident prose.

Failures are:
  * a conclusion drawn outside the observed window
  * an unqualified all-time claim on a partial window
  * an answer with no observation window stated
  * a chronology error (earliest after latest)
  * history attributed to the wrong company
  * an exception

Run:
    cd intelligence-engine
    INSTITUTIONAL_WAREHOUSE_ROOT=/tmp/wh_acceptance PYTHONPATH=. \
        python3 scripts/historical_intelligence_acceptance_v1.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from historical_intelligence import intent  # noqa: E402
from historical_intelligence.production import ask, company_coverage, health  # noqa: E402
from institutional_warehouse import store  # noqa: E402

# Phrases that assert more history than a partial window can support.
OVERCLAIM = re.compile(
    r"\b(cheapest ever|dearest ever|highest ever|lowest ever|all[- ]time (low|high)|"
    r"in its history|never been|always been|record (low|high))\b",
    re.IGNORECASE,
)

TEMPLATES: tuple[tuple[str, str], ...] = (
    # (category, template)
    ("trend_price", "Show {s} price trend since 2010"),
    ("trend_price", "How has {s} share price evolved over the last 10 years?"),
    ("trend_revenue", "Show {s} revenue growth since 2005"),
    ("trend_revenue", "How has {s} revenue trended over time?"),
    ("trend_profit", "Show {s} profit history"),
    ("trend_roe", "Explain {s} ROE history"),
    ("trend_margin", "How has {s} net margin changed over time?"),
    ("trend_debt", "Has {s} leverage improved historically?"),
    ("valuation", "How has {s} valuation changed over twenty years?"),
    ("valuation", "Is {s} expensive relative to its own history?"),
    ("valuation_extreme", "When was {s} historically cheapest on price to book?"),
    ("valuation_extreme", "When was {s} P/E highest?"),
    ("events", "Show the corporate event timeline for {s}"),
    ("events", "What dividends has {s} declared historically?"),
    ("cycle", "What happened to {s} during COVID?"),
    ("cycle", "How did {s} behave during the global financial crisis?"),
    ("year", "How did {s} perform in 2019?"),
    ("all_time", "What is the lowest {s} has ever traded?"),
)

COMPARISON_TEMPLATES = (
    ("comparison", "Compare {a} versus {b} price history"),
    ("comparison", "Compare {a} and {b} revenue growth over the last 10 years"),
)


def universe(limit: int = 14) -> list[str]:
    """Companies with the deepest price history, so the suite exercises real series."""
    from institutional_warehouse import db

    table = db.physical_table("daily_market_history")
    rows = db.query(
        f"SELECT sys_entity AS symbol, COUNT(*) AS n FROM {table}"
        f" WHERE sys_entity IS NOT NULL GROUP BY sys_entity ORDER BY COUNT(*) DESC LIMIT ?",
        (limit,),
    )
    return [str(r["symbol"]) for r in rows if r.get("symbol")]


def build_questions(symbols: list[str], target: int = 250) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for symbol in symbols:
        for category, template in TEMPLATES:
            out.append({"category": category, "question": template.format(s=symbol),
                        "symbol": symbol})
    for index, symbol in enumerate(symbols):
        other = symbols[(index + 1) % len(symbols)]
        for category, template in COMPARISON_TEMPLATES:
            out.append({"category": category,
                        "question": template.format(a=symbol, b=other), "symbol": symbol,
                        "peer": other})
    return out[:target]


def audit(case: dict[str, str], result: dict[str, Any]) -> list[str]:
    """Every way an answer can be dishonest. Empty list means the answer is sound."""
    problems: list[str] = []
    answer = str(result.get("answer") or "")
    coverage = result.get("coverage") or {}
    guard = result.get("guard") or {}
    conclusions = result.get("conclusions") or []

    if not result.get("ok"):
        problems.append(f"not_ok:{result.get('error')}")
        return problems

    if not answer.strip():
        problems.append("empty_answer")

    # An answer must always say what window it speaks for.
    window = result.get("observation_window")
    if conclusions and not window:
        problems.append("no_observation_window")

    # Chronology must be sane.
    earliest, latest = coverage.get("earliest"), coverage.get("latest")
    if earliest and latest:
        from historical_intelligence import periods

        a, b = periods.comparable(earliest), periods.comparable(latest)
        if a and b and a > b:
            problems.append("chronology_inverted")

    # Nothing may be concluded when the guard refused.
    if not guard.get("may_conclude", True) and conclusions:
        problems.append("concluded_outside_window")

    # An all-time claim is only allowed on a fully covered window.
    if OVERCLAIM.search(answer) and not guard.get("full_history_claim_allowed"):
        problems.append("unqualified_all_time_claim")

    # The answer must be about the company asked about.
    if result.get("symbol") and result["symbol"] != case["symbol"]:
        problems.append("wrong_company")

    # A coverage-limited reply must disclose the limit rather than imply completeness.
    if result.get("coverage_limited") and conclusions:
        disclosed = any(token in answer.lower() for token in
                        ("observed", "unavailable", "not available", "no claim",
                         "not observed", "only", "window"))
        if not disclosed:
            problems.append("undisclosed_coverage_limit")

    return problems


def main() -> int:
    report = health()
    symbols = universe()
    if not symbols:
        print(json.dumps({"suite": "historical_intelligence_acceptance_v1",
                          "error": "warehouse_has_no_price_history"}, indent=2))
        return 1

    cases = build_questions(symbols)
    results: list[dict[str, Any]] = []
    started = time.perf_counter()

    for case in cases:
        t0 = time.perf_counter()
        try:
            answer = ask(case["question"], symbol=case["symbol"],
                         peers=[case["peer"]] if case.get("peer") else None)
            problems = audit(case, answer)
        except Exception as exc:
            answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            problems = [f"exception:{type(exc).__name__}"]
        results.append({
            "category": case["category"],
            "question": case["question"],
            "symbol": case["symbol"],
            "coverage_limited": bool(answer.get("coverage_limited")),
            "reasoned": bool(answer.get("conclusions")),
            "confidence": answer.get("confidence"),
            "module": answer.get("module"),
            "problems": problems,
            "answer": str(answer.get("answer") or "")[:400],
            "ms": int((time.perf_counter() - t0) * 1000),
        })

    passed = [r for r in results if not r["problems"]]
    limited = [r for r in passed if r["coverage_limited"]]
    reasoned = [r for r in passed if r["reasoned"]]
    by_category: dict[str, dict[str, int]] = {}
    for entry in results:
        bucket = by_category.setdefault(entry["category"], {"n": 0, "pass": 0, "limited": 0,
                                                            "reasoned": 0})
        bucket["n"] += 1
        bucket["pass"] += 0 if entry["problems"] else 1
        bucket["limited"] += 1 if entry["coverage_limited"] else 0
        bucket["reasoned"] += 1 if entry["reasoned"] else 0

    problems: dict[str, int] = {}
    for entry in results:
        for problem in entry["problems"]:
            key = problem.split(":")[0]
            problems[key] = problems.get(key, 0) + 1

    summary = {
        "suite": "historical_intelligence_acceptance_v1",
        "questions": len(results),
        "passed": len(passed),
        "failed": len(results) - len(passed),
        "pass_rate_pct": round(100.0 * len(passed) / max(len(results), 1), 1),
        "answers_with_reasoning": len(reasoned),
        "answers_coverage_limited": len(limited),
        "honesty_violations": problems,
        "companies": len(symbols),
        "warehouse_rows_available": report.get("historical_rows_available"),
        "elapsed_s": round(time.perf_counter() - started, 1),
    }
    print(json.dumps(summary, indent=2))
    print("\nBy category:")
    for category, bucket in sorted(by_category.items()):
        print(f"  {category:18} n={bucket['n']:3} pass={bucket['pass']:3} "
              f"reasoned={bucket['reasoned']:3} coverage_limited={bucket['limited']:3}")

    failures = [r for r in results if r["problems"]][:12]
    if failures:
        print("\nFailures:")
        for entry in failures:
            print(f"  [{','.join(entry['problems'])}] {entry['question']}")
            print(f"      {entry['answer'][:220]}")

    print("\nSample answers:")
    for entry in results[:3]:
        print(f"  Q: {entry['question']}")
        print(f"     {entry['answer'][:260]}")

    out = Path("/tmp/historical_intelligence_acceptance_v1.json")
    out.write_text(json.dumps({"summary": summary, "by_category": by_category,
                               "results": results}, indent=2, default=str))
    print(f"\nwrote {out}")
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
