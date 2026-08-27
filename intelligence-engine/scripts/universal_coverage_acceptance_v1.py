#!/usr/bin/env python3
"""Phase 6.0 — Universal Coverage Acceptance v1.0

Proves that knowledge availability does not depend on the execution path:
every valuation / business / consensus question gathers the same expected
providers whether it goes through the UKO short-circuit or the desk gather.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASES = [
    {
        "id": "val_axis",
        "question": "Is Axis Bank expensive compared with its industry?",
        "family": "valuation",
        "must_use_any": ("valuation_terminal", "valuation_consensus"),
        "must_attempt": ("valuation_terminal", "industry_intelligence", "capiq_ikt"),
    },
    {
        "id": "val_tcs",
        "question": "Is TCS expensive compared with its industry?",
        "family": "valuation",
        "must_use_any": ("valuation_terminal",),
        "must_attempt": ("valuation_terminal", "valuation_consensus", "financial_statement_warehouse"),
    },
    {
        "id": "pb_axis",
        "question": "What is Axis Bank's price to book versus peers?",
        "family": "valuation",
        "must_use_any": ("valuation_terminal",),
        "must_attempt": ("valuation_terminal", "industry_intelligence"),
    },
    {
        "id": "consensus_infy",
        "question": "What is the consensus target price for Infosys?",
        "family": "consensus",
        "must_use_any": ("valuation_consensus",),
        "must_attempt": ("valuation_consensus", "capiq_ikt"),
    },
    {
        "id": "biz_axis",
        "question": "What does Axis Bank do?",
        "family": "business",
        "must_use_any": ("capiq_ikt", "business_intelligence", "company_memory"),
        "must_attempt": ("capiq_ikt", "business_intelligence"),
    },
    {
        "id": "screen_ashoka",
        "question": "Why would Ashoka Buildcon appear in a value screen?",
        "family": "screen",
        "must_use_any": ("valuation_terminal", "hedge_fund_screens"),
        "must_attempt": ("hedge_fund_screens", "valuation_terminal"),
    },
    {
        "id": "concept_bank_val",
        "question": "Why would a bank trade below its industry price to book?",
        "family": "industry",
        "must_use_any": ("industry_intelligence", "financial_concepts", "business_intelligence"),
        "must_attempt": ("industry_intelligence",),
    },
]


def _providers_from_uko(out: dict) -> set[str]:
    cov = out.get("coverage") or {}
    return set(cov.get("knowledge_sources_used") or cov.get("providers_used") or out.get("providers_used") or [])


def _selected_from_uko(out: dict) -> set[str]:
    diag = out.get("diagnostics") or {}
    planner = diag.get("planner") or {}
    return set(planner.get("selected") or cov_selected(out))


def cov_selected(out: dict) -> list[str]:
    return list((out.get("coverage") or {}).get("providers_selected") or [])


def run_case(case: dict) -> dict:
    from knowledge_unification.production import answer_for_ask
    from universal_knowledge.production import gather, for_ask_pipeline

    q = case["question"]
    t0 = time.perf_counter()
    uko = gather(q)
    short = answer_for_ask(q) or {}
    desk = for_ask_pipeline(q)
    elapsed = round((time.perf_counter() - t0) * 1000.0, 1)

    uko_used = _providers_from_uko(uko)
    short_used = set(short.get("providers_used") or [])
    desk_used = set(desk.get("providers_used") or [])
    selected = _selected_from_uko(uko)

    failures: list[str] = []

    # Expected providers must have been attempted.
    for pid in case["must_attempt"]:
        if pid not in selected and pid not in uko_used:
            failures.append(f"not_attempted:{pid}")

    # At least one of the must_use_any providers must contribute.
    if not any(p in uko_used for p in case["must_use_any"]):
        failures.append(f"missing_use_any:{case['must_use_any']}")

    # Route independence: short-circuit and desk gather must share the hard core.
    core = set(case["must_use_any"])
    if short_used and uko_used:
        if not (short_used & core) and not (uko_used & core):
            failures.append("short_and_uko_both_missing_core")
        # Desk must not lose providers the short path found in the core set.
        lost = (short_used & core) - desk_used
        if lost and short.get("uko"):
            # Desk gather is the same UKO gather — any loss is a real failure.
            failures.append(f"desk_lost_core:{sorted(lost)}")

    # Short and desk used sets for the core providers must match when both answer.
    if short_used and desk_used:
        if (short_used & core) != (desk_used & core):
            failures.append(
                f"route_divergence: short={sorted(short_used & core)} desk={sorted(desk_used & core)}"
            )

    if not uko.get("answerable") and case["family"] not in {"concept"}:
        # Valuation/business questions must be answerable under UKO.
        if case["family"] in {"valuation", "consensus", "business", "screen"}:
            failures.append("uko_not_answerable")

    return {
        "id": case["id"],
        "question": q,
        "family": case["family"],
        "pass": not failures,
        "failures": failures,
        "uko_used": sorted(uko_used),
        "short_used": sorted(short_used),
        "desk_used": sorted(desk_used),
        "selected": sorted(selected),
        "coverage_pct": (uko.get("coverage") or {}).get("coverage_pct"),
        "summary": (uko.get("summary") or "")[:180],
        "latency_ms": elapsed,
        "missing": (uko.get("coverage") or {}).get("providers_missing") or [],
    }


def main() -> int:
    # Reset registry so newly registered providers are visible.
    import knowledge_unification.registry as reg_mod

    reg_mod._REGISTRY = None

    from universal_knowledge.production import health

    h = health()
    results = [run_case(c) for c in CASES]
    passed = sum(1 for r in results if r["pass"])
    report = {
        "suite": "universal_coverage_acceptance_v1",
        "version": "uko-6.0",
        "provider_count": h.get("provider_count"),
        "healthy_providers": h.get("healthy"),
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate_pct": round((passed / len(results)) * 100.0, 1) if results else 0.0,
        "results": results,
        "route_independence": all(
            not any(f.startswith("route_divergence") or f.startswith("desk_lost") for f in r["failures"])
            for r in results
        ),
    }

    out_dir = Path("/tmp/cursor") if Path("/tmp/cursor").exists() else Path("/tmp")
    out_path = out_dir / "universal_coverage_acceptance_v1.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("suite", "cases", "passed", "failed", "pass_rate_pct", "route_independence", "provider_count")}, indent=2))
    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"  [{mark}] {r['id']}: used={r['uko_used']} failures={r['failures']}")
    print(f"wrote {out_path}")
    return 0 if report["failed"] == 0 and report["route_independence"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
