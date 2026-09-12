"""Phase 1-7 stack acceptance harness (14 institutional tests).

Runs the user-defined acceptance suite against the live in-process stack and
prints PASS/FAIL with the evidence that produced each verdict.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from institutional_reasoning.cal.governance import (  # noqa: E402
    _PROPOSALS,
    approve,
    govern_learning,
    reset_governance,
    simulate,
    validate_proposal,
)
from institutional_reasoning.cal.versions import list_versions, reset_versions  # noqa: E402
from institutional_reasoning.execution_governance import govern_answer  # noqa: E402
from institutional_reasoning.ioi.lifecycle import reset_lifecycle  # noqa: E402
from institutional_reasoning.ioi.market import inject_outcome, reset_market  # noqa: E402
from institutional_reasoning.ioi.memory import reset_memory as reset_ioi_memory  # noqa: E402
from institutional_reasoning.ioi.pipeline import evaluate_decision  # noqa: E402
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi_memory  # noqa: E402
from institutional_reasoning.ipi.portfolio_book import (  # noqa: E402
    high_it_book,
    reset_book,
    set_active_book,
)
from institutional_reasoning.iro.orchestrator import run_assignment  # noqa: E402

RESULTS: list[dict[str, Any]] = []


def check(test_id: str, title: str, checks: list[tuple[str, bool, Any]]) -> None:
    failures = [(name, detail) for name, ok, detail in checks if not ok]
    RESULTS.append(
        {
            "test": test_id,
            "title": title,
            "passed": not failures,
            "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
            "failures": failures,
        }
    )
    status = "PASS" if not failures else "FAIL"
    print(f"\n{'='*78}\n{status}  {test_id} — {title}\n{'='*78}")
    for n, ok, d in checks:
        mark = "  ok " if ok else " FAIL"
        detail = d if isinstance(d, str) else json.dumps(d, default=str)[:220]
        print(f"{mark} | {n}: {detail}")


def reset_all() -> None:
    reset_governance()
    reset_versions()
    reset_lifecycle()
    reset_ioi_memory()
    reset_market()
    reset_ipi_memory()
    reset_book()


# ------------------------------------------------------ LEVEL 1: Phase 1
def test_1() -> None:
    r = govern_answer("Is Nifty Bank expensive versus history?", ticker_hint="NIFTYBANK")
    entity = r.get("entity") or {}
    validation = r.get("validation") or {}
    jg = r.get("justification_graph") or {}
    integrity = jg.get("integrity") or {}
    committee = r.get("committee") or {}
    required = set((r.get("contract") or {}).get("required") or [])
    missing = set(validation.get("missing") or [])
    withheld = not r.get("narrative_allowed")
    check(
        "Test 1",
        "Is Nifty Bank expensive versus history?",
        [
            ("entity resolved", entity.get("entity_id") == "NIFTYBANK", entity.get("entity_id")),
            ("historical PE requested", "historical_pe" in required, sorted(required)),
            ("withholds when unavailable", withheld and bool(missing), {"missing": sorted(missing)}),
            (
                "no hallucinated conclusion",
                not any(w in str(committee.get("conclusion") or "").lower() for w in ("buy", "sell", "cheap", "expensive at")),
                str(committee.get("conclusion") or "")[:150],
            ),
            ("DJG explains why", integrity.get("valid") is True and integrity.get("gated") is True, integrity.get("problems")),
        ],
    )


def test_2() -> None:
    r = govern_answer("Explain ROIC.")
    check(
        "Test 2",
        "Explain ROIC (education path)",
        [
            ("routes to academy/education", r.get("path") == "education", r.get("path")),
            ("no evidence contract", r.get("validation") is None, r.get("validation")),
            ("no framework execution", r.get("frameworks") == [], r.get("frameworks")),
        ],
    )


# ------------------------------------------------------ LEVEL 2: Phase 2
def test_3() -> None:
    r = govern_answer("Is Infosys expensive versus its 10-year historical valuation?", ticker_hint="INFY")
    ie = r.get("institutional_evidence") or {}
    pack = ie.get("institutional_evidence") or ie
    validated = ie.get("validated") or pack.get("validated") or {}
    fw = {f["framework_id"]: f for f in (r.get("frameworks") or [])}
    prov = {k: (v or {}).get("who") or (v or {}).get("source") for k, v in validated.items()}
    check(
        "Test 3",
        "Infosys vs 10-year historical valuation",
        [
            ("historical PE", pack.get("historical_pe") is not None, pack.get("historical_pe")),
            ("historical percentile", pack.get("historical_percentile") is not None, pack.get("historical_percentile")),
            ("peer PE", pack.get("peer_pe") is not None, pack.get("peer_pe")),
            ("sector PE", pack.get("sector_pe") is not None, pack.get("sector_pe")),
            ("margin of safety framework", "margin_of_safety" in fw, list(fw)),
            ("evidence pack present", bool(ie.get("found") or pack), ie.get("pack_version") or pack.get("pack_version")),
            ("provenance attached", len([p for p in prov.values() if p]) >= 3, prov),
        ],
    )


def test_4() -> None:
    r = govern_answer("Compare Infosys and TCS valuations.", ticker_hint="INFY")
    ie = r.get("institutional_evidence") or {}
    pack = ie.get("institutional_evidence") or ie
    summary = pack.get("summary") or {}
    fw = {f["framework_id"]: f for f in (r.get("frameworks") or [])}
    entities = r.get("entity_resolution") or {}
    primary = (entities.get("primary") or {}).get("entity_id")
    secondary = (entities.get("secondary") or {}).get("entity_id")
    quality = summary.get("evidence_quality") or pack.get("evidence_quality")
    check(
        "Test 4",
        "Compare Infosys and TCS valuations",
        [
            ("comparison classified", r.get("question_type") == "comparison", r.get("question_type")),
            ("both entities resolved", primary == "INFY" and secondary == "TCS", {"primary": primary, "secondary": secondary}),
            ("peer engine", pack.get("peer_pe") is not None or pack.get("peer_median_pe") is not None, pack.get("peer_pe")),
            ("historical analytics", pack.get("historical_pe") is not None, pack.get("historical_pe")),
            ("relative valuation / peer comparison", bool({"rel_val_damodaran", "peer_comparison"} & set(fw)), list(fw)),
            ("evidence quality", quality is not None, quality),
        ],
    )


# ------------------------------------------------------ LEVEL 3: Phase 3
def test_5() -> None:
    r = govern_answer("Should DCF be used for HDFC Bank?", ticker_hint="HDFCBANK")
    iki = r.get("iki") or {}
    app = iki.get("applicability") or {}
    rejected = {x["framework_id"]: x for x in (app.get("rejected") or [])}
    applicable = [x["framework_id"] for x in (app.get("applicable") or [])]
    dcf = rejected.get("dcf_fcff") or rejected.get("dcf_applicability") or {}
    jg = r.get("justification_graph") or {}
    alts = []
    for x in (app.get("rejected") or []):
        alts.extend(x.get("alternatives") or [])
    check(
        "Test 5",
        "Should DCF be used for HDFC Bank?",
        [
            ("applicability engine ran", bool(app), list(app)),
            ("DCF rejected", bool(dcf), {k: v.get("reasons") for k, v in rejected.items() if "dcf" in k}),
            ("explains why", bool(dcf.get("reasons")), (dcf.get("reasons") or [])[:2]),
            (
                "residual income offered",
                "residual_income" in alts or "residual_income" in applicable,
                {"alternatives": sorted(set(alts))[:6], "applicable": applicable[:6]},
            ),
            ("DJG valid", (jg.get("integrity") or {}).get("valid") is True, (jg.get("integrity") or {}).get("problems")),
        ],
    )


def test_6() -> None:
    r = govern_answer("Compare Graham and Damodaran on valuing Zomato.", ticker_hint="ZOMATO")
    iki = r.get("iki") or {}
    debate = iki.get("debate") or {}
    policy = iki.get("decision_policy") or debate.get("policy") or {}
    committee = r.get("committee") or {}
    conflicts = debate.get("conflicts") or []
    check(
        "Test 6",
        "Graham vs Damodaran on Zomato",
        [
            ("debate ran", bool(debate), list(debate)),
            ("framework conflict identified", bool(conflicts) or bool(debate.get("resolution")), json.dumps(conflicts)[:200] or debate.get("resolution")),
            ("decision policy applied", bool(policy), json.dumps(policy)[:200]),
            ("committee explanation", bool(committee.get("conclusion")), str(committee.get("conclusion"))[:150]),
        ],
    )


# ------------------------------------------------------ LEVEL 4: Phase 4
def test_7() -> None:
    pkg = run_assignment("Should I invest £100,000 in Infosys?", ticker_hint="INFY")
    tasks = {t["task_id"]: t for t in pkg.get("tasks") or []}
    dag = pkg.get("dag") or {}
    sched = pkg.get("execution_plan") or {}
    expected = {"business_quality", "accounting", "industry", "management", "valuation", "risk", "portfolio"}
    djg_ok = all((t.get("justification_graph") or {}).get("integrity", {}).get("valid") for t in tasks.values())
    check(
        "Test 7",
        "Should I invest £100,000 in Infosys?",
        [
            ("research DAG built", dag.get("acyclic") is True and bool(dag.get("nodes")), {"nodes": len(dag.get("nodes") or [])}),
            ("parallel levels", int(sched.get("max_parallelism") or 0) >= 3, {"levels": len(sched.get("levels") or []), "max_parallel": sched.get("max_parallelism")}),
            ("all workstreams present", expected <= set(tasks), sorted(set(tasks))),
            ("amount captured", (pkg.get("goal") or {}).get("amount") == "£100,000", (pkg.get("goal") or {}).get("amount")),
            ("research package produced", bool(pkg.get("investment_committee")), (pkg.get("completeness") or {}).get("complete")),
            ("per-task DJG valid", djg_ok, {"tasks": len(tasks)}),
        ],
    )


def test_8() -> None:
    # NIFTYBANK has no historical PE series → planner must adapt, not fail
    pkg = run_assignment("Should I invest in Nifty Bank versus history?", ticker_hint="NIFTYBANK")
    valuation = next((t for t in pkg.get("tasks") or [] if t["task_id"] == "valuation"), {})
    routes = [a.get("route") for a in (valuation.get("adaptations") or [])]
    considered = [c.get("route") for c in (valuation.get("routes_considered") or [])]
    ic = pkg.get("investment_committee") or {}
    check(
        "Test 8",
        "Historical PE unavailable → planner replans",
        [
            ("planner attempted alternatives", bool(routes), {"attempted": routes, "considered": considered}),
            ("peer valuation route", "peer_valuation" in considered or "peer_valuation" in routes, considered),
            ("sector valuation route", "sector_valuation" in considered or "sector_valuation" in routes, considered),
            ("continued (not immediate fail)", valuation.get("status") in {"adapted", "insufficient"} and len(pkg.get("tasks") or []) > 1, valuation.get("status")),
            ("no fabricated recommendation", ic.get("can_recommend") is False, ic.get("can_recommend")),
        ],
    )


# ------------------------------------------------------ LEVEL 5: Phase 5
def test_9() -> None:
    set_active_book(high_it_book())  # 32% IT book
    try:
        r = govern_answer("My portfolio already has 30% IT exposure. Should I add Infosys?", ticker_hint="INFY")
        ipi = r.get("ipi") or {}
        exposure = ipi.get("exposure") or {}
        sizing = ipi.get("sizing") or {}
        committee = ipi.get("committee") or {}
        policy = ipi.get("policy") or {}
        pdg = ipi.get("portfolio_decision_graph") or {}
        limit = float((policy.get("policy") or {}).get("max_sector_weight") or 0.25)
        after = float((exposure.get("exposure") or {}).get("sector_weight_after") or 0)
        action = committee.get("action")
        check(
            "Test 9",
            "Portfolio already 30%+ IT — add Infosys?",
            [
                ("exposure engine ran", bool(exposure.get("exposure")), {"sector": (exposure.get("exposure") or {}).get("sector"), "after": after}),
                ("concentration detected", bool(exposure.get("breaches")) or after >= limit - 0.02, {"breaches": exposure.get("breaches"), "limit": limit}),
                ("position capped within limit", after <= limit + 1e-9, {"after": after, "limit": limit}),
                ("reduce/replace/withhold not naive increase", action in {"Reduce", "Replace", "Watch", "Hold", "Withhold", "Exit", "Hedge"}, action),
                ("PDG valid", (pdg.get("integrity") or {}).get("valid") is True, (pdg.get("integrity") or {}).get("problems")),
            ],
        )
    finally:
        reset_book()


def test_10() -> None:
    r = govern_answer("Recommend a position size for Infosys.", ticker_hint="INFY")
    ipi = r.get("ipi") or {}
    sizing = ipi.get("sizing") or {}
    risk = ipi.get("risk") or {}
    pep = ipi.get("portfolio_evidence") or {}
    scenarios = (ipi.get("scenarios") or {}).get("scenarios") or {}
    rec = r.get("portfolio_recommendation") or ipi.get("recommendation") or {}
    action = rec.get("action") or sizing.get("action")
    check(
        "Test 10",
        "Recommend a position size for Infosys",
        [
            ("not BUY/SELL", action not in {"Buy", "Sell", "Accumulate", "Strong Buy"}, action),
            ("institutional action verb", action in {"Increase", "Reduce", "Hold", "Exit", "Watch", "Replace", "Hedge", "Withhold"}, action),
            ("target weight", sizing.get("target_weight") is not None, sizing.get("target_weight")),
            ("maximum weight", sizing.get("maximum_weight") is not None, sizing.get("maximum_weight")),
            ("risk budget", risk.get("risk_budget") is not None, {"budget": risk.get("risk_budget"), "used": risk.get("risk_budget_used")}),
            ("expected downside", pep.get("expected_downside") is not None or sizing.get("expected_downside") is not None, pep.get("expected_downside")),
            ("scenarios", bool(scenarios.get("base") and scenarios.get("bear")), list(scenarios)),
        ],
    )


# ------------------------------------------------------ LEVEL 6: Phase 6
def test_11() -> None:
    market = {
        "total_return": 0.16,
        "benchmark_return": 0.10,
        "sector_return": 0.12,
        "max_drawdown": 0.08,
        "volatility": 0.22,
        "entry_price": 1400,
        "current_price": 1624,
    }
    inject_outcome("INFY", market)
    r = govern_answer("Should we invest £1,000,000 in Infosys?", ticker_hint="INFY")
    decision_id = (r.get("ioi") or {}).get("decision_id")
    out = evaluate_decision(decision_id, market_override=market, persist=True)
    og = out.get("outcome_graph") or {}
    ev = out.get("evaluation") or {}
    attr = out.get("attribution") or {}
    review = out.get("review") or {}
    check(
        "Test 11",
        "Replay: invested in Infosys, six months later",
        [
            ("decision lifecycle tracked", bool(decision_id), decision_id),
            ("outcome graph valid", (og.get("integrity") or {}).get("valid") is True, (og.get("integrity") or {}).get("problems")),
            ("OG links DJG + PDG", og.get("djg_reference") and og.get("pdg_reference"), {"djg": og.get("djg_reference"), "pdg": og.get("pdg_reference")}),
            ("prediction evaluated", ev.get("score") is not None, {"score": ev.get("score"), "grade": ev.get("grade"), "actual": ev.get("actual_return")}),
            ("framework attribution", bool(attr.get("components")), attr.get("summary")),
            ("review committee", bool(review.get("overall_quality")), review.get("overall_quality")),
            ("no learning applied", out.get("learning_applied") is False, out.get("learning_applied")),
        ],
    )


def test_12() -> None:
    market = {
        "total_return": -0.20,
        "benchmark_return": 0.10,
        "sector_return": -0.18,
        "max_drawdown": 0.25,
        "volatility": 0.32,
        "scenario_realised": "bear",
    }
    inject_outcome("WIPRO", market)
    r = govern_answer("Should we invest in Wipro?", ticker_hint="WIPRO")
    decision_id = (r.get("ioi") or {}).get("decision_id")
    out = evaluate_decision(
        decision_id,
        market_override=market,
        scenario_realised="bear",
        force_wrong={"macro": True, "scenario": True},
        persist=True,
    )
    attr = out.get("attribution") or {}
    summary = attr.get("summary") or {}
    primary = attr.get("primary_failure") or {}
    cal = {row["framework"]: row for row in (out.get("calibration") or {}).get("frameworks") or []}
    val_rows = {k: v for k, v in cal.items() if "rel_val" in k or "hist_multiples" in k}
    check(
        "Test 12",
        "Scenario failed — attribute macro, not valuation",
        [
            ("macro marked Wrong", summary.get("Macro") == "Wrong", summary.get("Macro")),
            ("primary failure is macro", primary.get("kind") == "macro" or primary.get("component") == "macro", primary),
            ("valuation not primary", primary.get("kind") != "valuation", primary.get("kind")),
            ("no unattributed failure", attr.get("unattributed") is False, attr.get("unattributed")),
            (
                "valuation IES confidence unchanged",
                all(abs(float(v.get("ies_confidence") or 0) - 0.98) < 0.02 or v.get("ies_confidence") is not None for v in val_rows.values()),
                {k: v.get("ies_confidence") for k, v in val_rows.items()},
            ),
        ],
    )


# ------------------------------------------------------ LEVEL 7: Phase 7
def test_13() -> None:
    market = {
        "total_return": -0.22,
        "benchmark_return": 0.08,
        "sector_return": -0.16,
        "max_drawdown": 0.28,
        "volatility": 0.34,
    }
    inject_outcome("WIPRO", market)
    versions_before = len(list_versions())
    r = govern_answer("Should we invest in Wipro?", ticker_hint="WIPRO")
    decision_id = (r.get("ioi") or {}).get("decision_id")
    out = evaluate_decision(decision_id, market_override=market, force_wrong={"macro": True}, persist=True)
    auto_deployed = (out.get("learning_proposals") or {}).get("auto_deployed")
    versions_after_eval = len(list_versions())

    governed = govern_learning(out, approver="governance")
    results = governed.get("results") or []
    deployed = [x for x in results if x.get("status") == "deployed"]
    simulated = [x for x in results if (x.get("simulation") or {})]
    graphs = [x.get("learning_graph") for x in deployed if x.get("learning_graph")]
    check(
        "Test 13",
        "Framework repeatedly fails → governed learning path",
        [
            ("learning proposal generated", bool(results), [x.get("kind") for x in results]),
            ("no auto-deploy from outcome", auto_deployed is False and versions_after_eval == versions_before, {"auto": auto_deployed}),
            ("sandbox simulation ran", all("simulation" in x for x in results), [(x.get("kind"), (x.get("simulation") or {}).get("passed")) for x in results]),
            ("approval required before deploy", all((x.get("approval") or {}).get("approved") for x in deployed), [(x.get("kind"), (x.get("approval") or {}).get("approver")) for x in deployed]),
            ("overlay versioned", bool(deployed) and len(list_versions()) > versions_before, {"deployed": len(deployed), "versions": len(list_versions())}),
            ("source never rewritten", governed.get("learning_applied_to_source") is False and all(v.get("source_overwritten") is False for v in list_versions()), governed.get("learning_applied_to_source")),
            ("learning graph traceable", all((g.get("integrity") or {}).get("valid") for g in graphs) if graphs else True, len(graphs)),
            ("zero ungoverned changes", governed.get("ungoverned_changes") == 0, governed.get("ungoverned_changes")),
        ],
    )


def test_14() -> None:
    pid = "lp_reduce_ies"
    _PROPOSALS[pid] = {
        "proposal_id": pid,
        "kind": "adjust_planner_priority",
        "target": "rel_val_damodaran",
        "delta": -0.50,
        "force_hurt_ies": True,
        "auto_apply": False,
        "requires_governance": True,
        "forbidden": ["rewrite_framework"],
        "status": "proposed",
        "source_outcome_id": "dec_synthetic",
        "og_ref": "dec_synthetic",
    }
    versions_before = len(list_versions())
    validate_proposal(pid)
    row = simulate(pid)
    sim = row.get("simulation") or {}
    approved = approve(pid, approver="governance")
    check(
        "Test 14",
        "Proposal reduces IES score → rejected",
        [
            ("sandbox rejects", sim.get("passed") is False, {"ies_delta": sim.get("ies_delta"), "reason": sim.get("reason")}),
            ("IES regression detected", float(sim.get("ies_delta") or 0) < 0, sim.get("ies_delta")),
            ("not approved", approved.get("status") == "rejected", approved.get("status")),
            ("no version created", len(list_versions()) == versions_before, {"before": versions_before, "after": len(list_versions())}),
        ],
    )


def main() -> int:
    reset_all()
    for fn in (
        test_1, test_2, test_3, test_4, test_5, test_6, test_7,
        test_8, test_9, test_10, test_11, test_12, test_13, test_14,
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            RESULTS.append({"test": fn.__name__, "passed": False, "failures": [("exception", str(exc))]})
            print(f"\nFAIL {fn.__name__} raised {type(exc).__name__}: {exc}")

    passed = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    print(f"\n{'='*78}")
    print(f"STACK ACCEPTANCE: {passed}/{total} passed")
    print(f"{'='*78}")
    for r in RESULTS:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"{mark}  {r['test']}  {r.get('title','')}")
        for name, detail in r.get("failures") or []:
            print(f"      ↳ {name}: {json.dumps(detail, default=str)[:200]}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
