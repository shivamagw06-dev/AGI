"""Full-platform evaluation: £500m India equity fund mandate case.

Mandate:
  * £500,000,000 India-focused equity fund
  * Overweight IT and financials, underweight industrials
  * Maximum 5% single position, 20% sector cap
  * Analyst proposes increasing Infosys after a strong quarter

Exercises the complete Phase 1-7 stack and prints the institutional answer plus
the machine-checkable artefacts behind it.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from institutional_reasoning.cal.governance import govern_learning, reset_governance  # noqa: E402
from institutional_reasoning.cal.versions import list_versions, reset_versions  # noqa: E402
from institutional_reasoning.execution_governance import govern_answer, telemetry_rows  # noqa: E402
from institutional_reasoning.ioi.lifecycle import get_decision, reset_lifecycle  # noqa: E402
from institutional_reasoning.ioi.market import inject_outcome, reset_market  # noqa: E402
from institutional_reasoning.ioi.memory import reset_memory as reset_ioi_memory  # noqa: E402
from institutional_reasoning.ioi.pipeline import evaluate_decision  # noqa: E402
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi_memory  # noqa: E402
from institutional_reasoning.ipi.portfolio_book import reset_book, set_active_book  # noqa: E402
from institutional_reasoning.ipi.schema import PortfolioHolding, PortfolioPolicy  # noqa: E402
from institutional_reasoning.iro.orchestrator import run_assignment  # noqa: E402
from institutional_reasoning.iro.telemetry import orchestration_summary  # noqa: E402

AUM_GBP = 500_000_000

MANDATE_QUESTION = (
    "We manage a £500 million India-focused equity fund that is overweight IT and "
    "financials and underweight industrials, with a maximum 5% position size and a "
    "20% sector cap. An analyst recommends increasing Infosys after a strong quarter. "
    "Should we increase, hold, reduce another position to fund it, or reject?"
)


def fund_book() -> dict[str, Any]:
    """£500m India fund: overweight IT + financials, underweight industrials."""
    policy = PortfolioPolicy(
        max_stock_weight=0.05,      # mandate: 5% single position
        max_sector_weight=0.20,     # mandate: 20% sector cap
        max_country_weight=1.00,    # India-focused by design
        max_theme_weight=0.30,
        min_liquidity_score=0.55,
        max_drawdown=0.25,
        max_single_name_risk_contribution=0.18,
        risk_budget=0.12,
        cash_reserve_min=0.03,
    ).to_dict()

    holdings = [
        # IT — overweight (22% vs 20% cap)
        PortfolioHolding("TCS", 0.055, "it_services", "it_services", theme="ai_services",
                         beta=0.90, volatility=0.20,
                         factors={"quality": 0.90, "value": 0.35, "growth": 0.45, "momentum": 0.35}).to_dict(),
        PortfolioHolding("INFY", 0.050, "it_services", "it_services", theme="ai_services",
                         beta=0.95, volatility=0.24,
                         factors={"quality": 0.85, "value": 0.40, "growth": 0.50, "momentum": 0.40}).to_dict(),
        PortfolioHolding("HCLTECH", 0.045, "it_services", "it_services", theme="ai_services",
                         beta=1.00, volatility=0.25,
                         factors={"quality": 0.75, "value": 0.45, "growth": 0.50, "momentum": 0.40}).to_dict(),
        PortfolioHolding("WIPRO", 0.040, "it_services", "it_services", theme="ai_services",
                         beta=1.05, volatility=0.28,
                         factors={"quality": 0.70, "value": 0.50, "growth": 0.40, "momentum": 0.35}).to_dict(),
        PortfolioHolding("TECHM", 0.030, "it_services", "it_services", theme="ai_services",
                         beta=1.10, volatility=0.30,
                         factors={"quality": 0.65, "value": 0.55, "growth": 0.40, "momentum": 0.30}).to_dict(),
        # Financials — overweight (21%)
        PortfolioHolding("HDFCBANK", 0.050, "banks", "private_bank",
                         beta=0.95, volatility=0.23,
                         factors={"quality": 0.80, "value": 0.40, "growth": 0.50, "momentum": 0.30}).to_dict(),
        PortfolioHolding("ICICIBANK", 0.050, "banks", "private_bank",
                         beta=1.00, volatility=0.24,
                         factors={"quality": 0.75, "value": 0.45, "growth": 0.55, "momentum": 0.40}).to_dict(),
        PortfolioHolding("KOTAKBANK", 0.045, "banks", "private_bank",
                         beta=0.95, volatility=0.24).to_dict(),
        PortfolioHolding("AXISBANK", 0.040, "banks", "private_bank",
                         beta=1.10, volatility=0.27).to_dict(),
        PortfolioHolding("SBIN", 0.025, "banks", "psu_bank",
                         beta=1.20, volatility=0.30, liquidity_score=0.90).to_dict(),
        # Industrials — underweight (6%)
        PortfolioHolding("LT", 0.035, "industrials", "capital_goods",
                         beta=1.10, volatility=0.26).to_dict(),
        PortfolioHolding("SIEMENS", 0.025, "industrials", "capital_goods",
                         beta=1.00, volatility=0.28, liquidity_score=0.65).to_dict(),
        # Energy / consumer / telecom / materials / pharma / auto — remainder of the book
        PortfolioHolding("RELIANCE", 0.050, "energy_conglomerate", "conglomerate",
                         beta=1.10, volatility=0.26).to_dict(),
        PortfolioHolding("ONGC", 0.020, "energy_conglomerate", "upstream",
                         beta=1.15, volatility=0.30).to_dict(),
        PortfolioHolding("NESTLEIND", 0.040, "fmcg", "staples",
                         beta=0.55, volatility=0.16).to_dict(),
        PortfolioHolding("HINDUNILVR", 0.030, "fmcg", "staples",
                         beta=0.60, volatility=0.17).to_dict(),
        PortfolioHolding("ASIANPAINT", 0.030, "fmcg", "paints",
                         beta=0.70, volatility=0.20).to_dict(),
        PortfolioHolding("BHARTIARTL", 0.040, "telecom", "telecom",
                         beta=1.05, volatility=0.28).to_dict(),
        PortfolioHolding("SUNPHARMA", 0.040, "pharma", "pharma",
                         beta=0.80, volatility=0.22).to_dict(),
        PortfolioHolding("CIPLA", 0.030, "pharma", "pharma",
                         beta=0.85, volatility=0.23).to_dict(),
        PortfolioHolding("MARUTI", 0.035, "auto", "auto_oem",
                         beta=1.05, volatility=0.25).to_dict(),
        PortfolioHolding("TATAMOTORS", 0.035, "auto", "auto_oem",
                         beta=1.30, volatility=0.34).to_dict(),
        PortfolioHolding("ULTRACEMCO", 0.030, "materials", "cement",
                         beta=1.00, volatility=0.24).to_dict(),
        PortfolioHolding("JSWSTEEL", 0.025, "materials", "steel",
                         beta=1.25, volatility=0.32).to_dict(),
        PortfolioHolding("TITAN", 0.025, "consumer_discretionary", "retail",
                         beta=0.95, volatility=0.26).to_dict(),
        PortfolioHolding("DMART", 0.020, "consumer_discretionary", "retail",
                         beta=0.90, volatility=0.27, liquidity_score=0.70).to_dict(),
        PortfolioHolding("POWERGRID", 0.020, "utilities", "power",
                         beta=0.65, volatility=0.19).to_dict(),
    ]
    invested = sum(h["weight"] for h in holdings)
    return {
        "portfolio_id": "agib_india_500m",
        "name": "AGIB India Equity Fund (£500m)",
        "base_currency": "GBP",
        "aum_gbp": AUM_GBP,
        "cash_weight": round(1.0 - invested, 4),
        "policy": policy,
        "holdings": holdings,
    }


def money(weight: float | None) -> str:
    if weight is None:
        return "n/a"
    return f"£{float(weight) * AUM_GBP/1_000_000:,.1f}m"


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{float(x)*100:.2f}%"


def section(title: str) -> None:
    print(f"\n{'='*86}\n{title}\n{'='*86}")


def main() -> int:
    reset_governance()
    reset_versions()
    reset_lifecycle()
    reset_ioi_memory()
    reset_market()
    reset_ipi_memory()
    book = fund_book()
    set_active_book(book)

    try:
        # ---------------------------------------------------------- 1. Research plan
        section("1. RESEARCH PLAN (Phase 4 — Institutional Research Orchestration)")
        package = run_assignment(
            "Should the fund increase Infosys after a strong quarter?",
            ticker_hint="INFY",
        )
        plan = package.get("plan") or {}
        dag = package.get("dag") or {}
        sched = package.get("execution_plan") or {}
        print(f"Goal type        : {(package.get('goal') or {}).get('goal_type')}")
        print(f"Entity           : {(package.get('goal') or {}).get('entity_id')}")
        print(f"Tasks            : {len(package.get('tasks') or [])}  (DAG acyclic={dag.get('acyclic')})")
        print(f"Execution levels : {len(sched.get('levels') or [])}, max parallelism {sched.get('max_parallelism')}")
        for i, level in enumerate(sched.get("levels") or []):
            print(f"   level {i}: {', '.join(level)}")

        section("2. FRAMEWORK EXECUTION + DJG (Phases 1-3)")
        for t in package.get("tasks") or []:
            jg = t.get("justification_graph") or {}
            integ = jg.get("integrity") or {}
            counts = jg.get("counts") or {}
            flag = "OK " if integ.get("valid") else "BAD"
            print(
                f"[{flag}] {t['task_id']:<16} status={t['status']:<13} "
                f"DJG nodes={counts.get('nodes'):<3} edges={counts.get('edges'):<3} "
                f"gated={integ.get('gated')}"
            )
            if t.get("missing_evidence"):
                print(f"        missing: {', '.join(t['missing_evidence'][:6])}")
            if t.get("routes_considered"):
                print(f"        replan ladder: {[r['route'] for r in t['routes_considered']]}")

        # Applicability: which frameworks ran vs were rejected
        research = govern_answer(MANDATE_QUESTION, ticker_hint="INFY")
        iki = research.get("iki") or {}
        app = iki.get("applicability") or {}
        print("\nApplicability (only applicable frameworks execute):")
        for row in (app.get("applicable") or [])[:8]:
            print(f"   RUN    {row['framework_id']:<26} score={row.get('score')}")
        for row in (app.get("rejected") or [])[:8]:
            reasons = "; ".join((row.get("reasons") or [])[:1])
            print(f"   REJECT {row['framework_id']:<26} {reasons}")

        section("3. PORTFOLIO EVIDENCE PACK (Phase 5 — Module 1)")
        ipi = research.get("ipi") or {}
        pep = ipi.get("portfolio_evidence") or {}
        ev = pep.get("evidence_fields") or {}
        print(f"Security             : {pep.get('security')} ({pep.get('symbol')})")
        print(f"Current PE           : {ev.get('current_pe')}")
        print(f"Historical PE        : {ev.get('historical_pe')}   Peer PE: {ev.get('peer_pe')}   Sector PE: {ev.get('sector_pe')}")
        print(f"ROIC                 : {ev.get('roic')}")
        print(f"Expected return      : {pct(pep.get('expected_return'))}")
        print(f"Expected downside    : {pct(pep.get('expected_downside'))}")
        print(f"Evidence coverage    : {pct(pep.get('evidence_coverage'))}")
        print(f"Research confidence  : {pct(pep.get('research_confidence'))}")
        print(f"Risk contribution    : {pep.get('risk_contribution')}")
        print(f"Liquidity            : {pep.get('liquidity')}")
        print(f"DJG reference        : {pep.get('djg_reference')}")

        section("4. EXPOSURE CONSTRAINTS (Phase 5 — Module 4)")
        exposure = ipi.get("exposure") or {}
        expo = exposure.get("exposure") or {}
        buckets = expo.get("sector_buckets") or {}
        cap = float((ipi.get("policy") or {}).get("policy", {}).get("max_sector_weight") or 0.20)
        print(f"Sector cap {pct(cap)} | single-name cap {pct((ipi.get('policy') or {}).get('policy', {}).get('max_stock_weight'))}")
        for sector, w in sorted(buckets.items(), key=lambda kv: -kv[1]):
            state = "OVER" if w > cap + 1e-9 else ("AT CAP" if abs(w - cap) < 0.005 else "ok")
            print(f"   {sector:<22} {pct(w):>8}  {state}")
        print(f"\nIT now               : {pct(expo.get('sector_weight_now'))}")
        print(f"IT after proposal    : {pct(expo.get('sector_weight_after'))}")
        print(f"Sector headroom      : {pct(expo.get('sector_headroom'))}  → max allowed INFY weight {pct(expo.get('max_allowed_weight'))}")
        for b in exposure.get("breaches") or []:
            print(f"   BREACH {b.get('kind')}: limit {b.get('limit')} projected {b.get('projected')} — {b.get('message')}")

        section("5. SCENARIOS (Phase 5 — Module 5)")
        scen = (ipi.get("scenarios") or {}).get("scenarios") or {}
        for name in ("bull", "base", "bear", "stress"):
            s = scen.get(name) or {}
            print(f"   {name:<7} return {pct(s.get('expected_return')):>9}  loss {pct(s.get('expected_loss')):>8}  p={s.get('probability')}  conf={s.get('confidence')}")
        print("\n   Named macro shocks:")
        for sh in ((ipi.get("scenarios") or {}).get("shocks") or [])[:7]:
            print(f"     {sh['label']:<22} return {pct(sh['expected_return']):>9}  p={sh['probability']}  frameworks={','.join(sh['affected_frameworks'][:2])}")

        section("6. RISK + PORTFOLIO POLICY (Phase 5 — Modules 3 & 6)")
        risk = ipi.get("risk") or {}
        policy = ipi.get("policy") or {}
        print(f"Volatility {risk.get('volatility')}  Beta {risk.get('beta')}  VaR95 {risk.get('var')}  ES95 {risk.get('expected_shortfall')}")
        print(f"Max drawdown {risk.get('maximum_drawdown')}  Tail {risk.get('tail_risk')}  Liquidity risk {risk.get('liquidity_risk')}")
        print(f"Risk contribution {risk.get('risk_contribution')} of budget {risk.get('risk_budget')} → used {pct(risk.get('risk_budget_used'))}")
        print(f"Risk drivers: {', '.join(risk.get('risk_drivers') or [])}")
        print(f"\nPolicy allowed      : {policy.get('allowed')}")
        print(f"Can own more        : {policy.get('can_own_more')}")
        print(f"Violates concentration: {policy.get('violates_concentration')}")
        print(f"Fits risk budget    : {policy.get('fits_risk_budget')}")
        print(f"Cash available      : {policy.get('cash_available')}  (cash {pct(book['cash_weight'])})")
        print(f"Policy reasons      : {', '.join(policy.get('reasons') or []) or 'none'}")
        rc = policy.get("replace_candidate")
        if rc:
            print(f"Funding candidate   : reduce {rc.get('symbol')} (currently {pct(rc.get('current_weight'))}) — {rc.get('reason')}")

        section("7. POSITION SIZING + PORTFOLIO COMMITTEE (Phase 5 — Modules 2 & 7)")
        sizing = ipi.get("sizing") or {}
        committee = ipi.get("committee") or {}
        print(f"Current weight  : {pct(sizing.get('current_weight'))}  ({money(sizing.get('current_weight'))})")
        print(f"Target weight   : {pct(sizing.get('target_weight'))}  ({money(sizing.get('target_weight'))})")
        print(f"Max / Min       : {pct(sizing.get('maximum_weight'))} / {pct(sizing.get('minimum_weight'))}")
        print(f"Conviction      : {sizing.get('conviction')}   Confidence {pct(sizing.get('confidence'))}")
        print(f"Sizing rationale: {sizing.get('reason')}")
        print("\nCommittee members:")
        for name, m in (committee.get("members") or {}).items():
            extra = ""
            if m.get("breaches"):
                extra = f" ({len(m['breaches'])} breach)"
            print(f"   {name:<10} vote={m.get('vote'):<9}{extra}")
        print(f"\nDECISION        : {committee.get('action')}")
        print(f"Can recommend   : {committee.get('can_recommend')}")
        print(f"Conclusion      : {committee.get('conclusion')}")

        section("8. PORTFOLIO DECISION GRAPH (Phase 5 — PDG)")
        pdg = ipi.get("portfolio_decision_graph") or {}
        integ = pdg.get("integrity") or {}
        print(f"PDG {pdg.get('run_id')}  valid={integ.get('valid')}  nodes={pdg.get('counts',{}).get('nodes')} edges={pdg.get('counts',{}).get('edges')}")
        print(f"Linked research DJG: {pdg.get('djg_reference')}")
        for n in pdg.get("nodes") or []:
            print(f"   {n['kind']:<26} {str(n['label'])[:70]}")

        section("9. WITHHELD / UNSUPPORTED COMPONENTS")
        validation = research.get("validation") or {}
        missing = validation.get("missing") or []
        rejected = validation.get("rejected") or {}
        withheld_tasks = [t for t in (package.get("tasks") or []) if t["status"] in {"insufficient", "not_applicable"}]
        print(f"Narrative allowed on research path: {research.get('narrative_allowed')}")
        print(f"Contract missing fields : {missing or 'none'}")
        print(f"Rejected evidence       : {rejected or 'none'}")
        print(f"Portfolio withheld      : {ipi.get('withheld')}")
        print(f"Unsupported recommendation emitted: {ipi.get('unsupported')}")
        if withheld_tasks:
            print("Withheld workstreams:")
            for t in withheld_tasks:
                print(f"   {t['task_id']:<16} {t['status']:<16} missing={', '.join(t.get('missing_evidence') or []) or 'n/a'}")
        ic = package.get("investment_committee") or {}
        print(f"\nResearch committee can_recommend: {ic.get('can_recommend')}")
        print(f"Research completeness: {(package.get('completeness') or {}).get('complete')}")

        section("10. WHAT EVIDENCE WOULD CHANGE THE DECISION")
        changers: list[str] = []
        for f in missing:
            changers.append(f"Supply validated `{f}` for INFY (currently missing → framework blocked)")
        for f, why in (rejected or {}).items():
            changers.append(f"Replace `{f}` (rejected: {why})")
        headroom = expo.get("sector_headroom")
        if headroom is not None and float(headroom) < 0.05:
            changers.append(
                f"Reduce IT elsewhere: each 1% cut in TCS/WIPRO/TECHM raises INFY headroom by 1% "
                f"(current headroom {pct(headroom)} vs 5% single-name cap)"
            )
        if float(risk.get("risk_budget_used") or 0) > 0.8:
            changers.append(f"Lower correlated IT risk contribution (budget used {pct(risk.get('risk_budget_used'))})")
        dd = (ipi.get("portfolio_evidence") or {}).get("expected_downside")
        if dd is not None:
            changers.append(f"A downside case better than {pct(dd)} would support a larger target weight")
        for t in withheld_tasks:
            if t.get("missing_evidence"):
                changers.append(f"Complete {t['task_id']} evidence: {', '.join(t['missing_evidence'][:3])}")
        for i, c in enumerate(dict.fromkeys(changers), 1):
            print(f"   {i}. {c}")

        section("11. TELEMETRY (Phase 1) + ORCHESTRATION (Phase 4)")
        rows = telemetry_rows(research, answer_id=research.get("run_id"))
        print(f"Telemetry rows emitted: {len(rows)}")
        for r in rows[:6]:
            print(
                f"   {str(r.get('framework_id') or r.get('question_type')):<26} "
                f"status={str(r.get('framework_status') or r.get('committee_stance'))[:22]:<24} "
                f"djg_valid={r.get('djg_valid')}"
            )
        osum = orchestration_summary(package)
        print(f"\nOrchestration: tasks={osum.get('tasks')} succeeded={osum.get('succeeded')} "
              f"failed={osum.get('failed')} adapted={osum.get('adapted_tasks')} "
              f"success_rate={osum.get('success_rate_pct')}% djg_coverage={osum.get('djg_coverage_pct')}%")

        section("12. OUTCOME TRACKING + LEARNING CANDIDATE (Phases 6-7)")
        ioi_handle = research.get("ioi") or {}
        decision_id = ioi_handle.get("decision_id")
        print(f"Decision lifecycle registered: {decision_id} (status={ioi_handle.get('status')})")
        life = get_decision(decision_id) if decision_id else None
        if life:
            print(f"   tracked weight {pct(life.get('position_weight'))}, benchmark {life.get('benchmark')}, reviews {life.get('review_dates')}")
            print(f"   research DJG {life.get('research_djg')} | portfolio PDG {life.get('portfolio_djg')}")

        # Simulate the review that would occur at the first review date.
        realised = {
            "total_return": -0.06,
            "benchmark_return": 0.04,
            "sector_return": -0.03,
            "max_drawdown": 0.14,
            "volatility": 0.26,
        }
        inject_outcome("INFY", realised)
        outcome = evaluate_decision(decision_id, market_override=realised, persist=True) if decision_id else {}
        if outcome.get("found"):
            evaluation = outcome.get("evaluation") or {}
            attribution = outcome.get("attribution") or {}
            review = outcome.get("review") or {}
            og = outcome.get("outcome_graph") or {}
            print(f"\nReview replay (realised {pct(realised['total_return'])} vs benchmark {pct(realised['benchmark_return'])}):")
            print(f"   score {evaluation.get('score')} grade {evaluation.get('grade')} | return error {evaluation.get('return_error')}")
            print(f"   attribution: {json.dumps(attribution.get('summary') or {})[:220]}")
            print(f"   primary failure: {(attribution.get('primary_failure') or {}).get('label')}")
            print(f"   unattributed failure: {attribution.get('unattributed')}")
            print(f"   review overall: {review.get('overall_quality')}")
            print(f"   outcome graph valid={(og.get('integrity') or {}).get('valid')} linked DJG+PDG="
                  f"{bool(og.get('djg_reference') and og.get('pdg_reference'))}")
            lp = outcome.get("learning_proposals") or {}
            print(f"   learning candidates generated: {lp.get('count')} (auto_deployed={lp.get('auto_deployed')})")

            governed = govern_learning(outcome, approver="governance")
            results = governed.get("results") or []
            print(f"\nLearning governance: {len(results)} proposals")
            for r in results[:6]:
                sim = r.get("simulation") or {}
                print(
                    f"   {r.get('kind'):<26} target={str(r.get('target'))[:20]:<20} "
                    f"sim_passed={sim.get('passed')} ies_delta={sim.get('ies_delta')} "
                    f"status={r.get('status')}"
                )
            print(f"   ungoverned changes: {governed.get('ungoverned_changes')}")
            print(f"   source rewritten  : {governed.get('learning_applied_to_source')}")
            print(f"   versioned overlays: {len(list_versions())}")

        # ------------------------------------------------------------- verdict
        section("INSTITUTIONAL ANSWER")
        action = committee.get("action")
        target = sizing.get("target_weight")
        current = sizing.get("current_weight")
        print(f"DECISION: {action} — Infosys target {pct(target)} ({money(target)}), currently {pct(current)} ({money(current)})")
        print(f"\n{committee.get('conclusion')}")
        print(f"\nBinding constraint: IT sector at {pct(expo.get('sector_weight_now'))} against a {pct(cap)} cap "
              f"leaves {pct(expo.get('sector_headroom'))} of headroom for Infosys.")
        if rc:
            print(f"Funding route if the fund still wants the increase: reduce {rc.get('symbol')} "
                  f"(currently {pct(rc.get('current_weight'))}).")
        print(f"\nWithheld: {'yes' if ipi.get('withheld') else 'no'} | "
              f"Unsupported recommendation: {'yes' if ipi.get('unsupported') else 'no'} | "
              f"PDG valid: {integ.get('valid')}")
        return 0
    finally:
        reset_book()


if __name__ == "__main__":
    raise SystemExit(main())
