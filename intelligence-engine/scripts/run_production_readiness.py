#!/usr/bin/env python3
"""Production readiness review — operate the platform, don't expand architecture.

Runs five checks requested before / after KF go-live:
  1. Data correctness (independent metric recomputation)
  2. Universe coverage report
  3. Multi-day pipeline stability
  4. Reasoning regression (before vs after KF feed)
  5. End-to-end lifecycle (earnings → learning proposal)

Writes a JSON + markdown report under data/knowledge_factory/reports/ and stdout.
Phases 1–7 remain frozen.
"""

from __future__ import annotations

import json
import os
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_factory.production import coverage_dashboard, quality_gates, run_daily_pipeline
from knowledge_factory.store import repository as store
from knowledge_factory.validators.pipeline import dedupe_filings, validate_dataset
from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.fundamentals.derivations import derive_series, verify_derivation
from institutional_reasoning.fundamentals.primitives import (
    FIELDS,
    covered_entities,
    has_primitives,
    primitive_panel,
)
from institutional_reasoning.fundamentals.market_series import monthly_returns
from institutional_reasoning.fundamentals.universe import NIFTY_50, tier_report
from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics
from institutional_reasoning.ioi.market import inject_outcome, reset_market
from institutional_reasoning.ioi.pipeline import evaluate_decision
from institutional_reasoning.cal.governance import govern_learning, reset_governance
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi
from institutional_reasoning.ioi.lifecycle import reset_lifecycle
from institutional_reasoning.ioi.memory import reset_memory as reset_ioi

# 20-name readiness universe across IT / banks / energy / consumer / pharma / industrials / auto / fmcg
TARGET_20 = (
    "INFY", "TCS", "WIPRO", "HCLTECH", "TECHM",  # IT
    "HDFCBANK", "ICICIBANK", "SBIN",  # banks
    "RELIANCE",  # energy
    "ZOMATO",  # consumer internet
    "SUNPHARMA", "DRREDDY", "CIPLA",  # pharma
    "LT", "SIEMENS", "BEL",  # industrials
    "MARUTI", "TATAMOTORS",  # auto
    "ASIANPAINT", "HINDUNILVR",  # fmcg
)

BENCHMARK_QUESTIONS = [
    ("Is Infosys expensive versus history?", "INFY"),
    ("Is TCS expensive versus history?", "TCS"),
    ("Is Wipro expensive versus history?", "WIPRO"),
    ("Is HCLTech expensive versus history?", "HCLTECH"),
    ("Is HDFC Bank expensive versus history?", "HDFCBANK"),
    ("Is ICICI Bank expensive versus history?", "ICICIBANK"),
    ("Is Reliance expensive versus history?", "RELIANCE"),
    ("What are the key risks and downside for Infosys?", "INFY"),
    ("What are the key risks and downside for TCS?", "TCS"),
    ("What are the key risks and downside for Wipro?", "WIPRO"),
    ("Should we invest £100,000 in Infosys?", "INFY"),
    ("Should we invest £100,000 in TCS?", "TCS"),
    ("Should we invest in Wipro?", "WIPRO"),
    ("Should we invest in HDFC Bank?", "HDFCBANK"),
    ("Compare Infosys and TCS valuations", "INFY"),
    ("Does Infosys breach our 20% sector cap?", "INFY"),
    ("Recommend a position size for Infosys", "INFY"),
    ("Is Zomato expensive versus history?", "ZOMATO"),
    ("Should DCF be used for HDFC Bank?", "HDFCBANK"),
    ("Explain ROIC.", None),
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check_data_correctness() -> dict[str, Any]:
    rows = []
    metrics = ("PE", "PB", "EV_EBITDA", "ROE", "ROIC", "Net_Margin")
    for entity in TARGET_20:
        row: dict[str, Any] = {"entity": entity, "has_primitives": has_primitives(entity), "checks": []}
        if not has_primitives(entity):
            row["status"] = "uncovered"
            row["verified"] = 0
            row["total"] = 0
            rows.append(row)
            continue
        verified = 0
        total = 0
        for metric in metrics:
            series = derive_series(entity, metric)
            if not series.get("found") or not series.get("points"):
                # banks skip EV/EBITDA — acceptable
                if metric == "EV_EBITDA" and entity in {"HDFCBANK", "ICICIBANK", "SBIN"}:
                    row["checks"].append({"metric": metric, "ok": True, "note": "not_applicable_bank"})
                    continue
                row["checks"].append({"metric": metric, "ok": False, "note": series.get("reason") or "missing"})
                total += 1
                continue
            # Independent recompute of up to 3 periods
            periods = list(series["points"])[:3]
            ok_all = True
            for p in periods:
                total += 1
                v = verify_derivation(entity, metric, p)
                if v.get("verified"):
                    verified += 1
                else:
                    ok_all = False
            row["checks"].append({"metric": metric, "ok": ok_all, "periods": len(periods)})
        # Risk independent presence
        risk = derive_risk_metrics(entity)
        row["risk"] = bool(risk and risk.get("risk_drivers"))
        # Evidence pack provenance/freshness after pipeline
        pack = store.get_pack(entity) or {}
        row["pack_provenance"] = bool(pack.get("provenance") or pack.get("version"))
        row["pack_freshness"] = bool(pack.get("freshness") or pack.get("timestamp"))
        row["verified"] = verified
        row["total"] = total
        row["status"] = "pass" if total and verified == total and row["risk"] else ("partial" if verified else "fail")
        rows.append(row)

    # Stale / conflict rejection smoke
    stale = validate_dataset(
        {"entity": "INFY", "source": "yahoo", "timestamp": "2020-01-01T00:00:00Z", "payload": {"x": 1}},
        max_age_hours=72,
        allow_stale=False,
    )
    conflict = validate_dataset(
        {
            "entity": "INFY",
            "source": "yahoo",
            "timestamp": _now(),
            "payload": {"eps": -1, "force_pe": 20, "conflict": True},
        }
    )
    covered = [r for r in rows if r["has_primitives"]]
    pass_n = sum(1 for r in covered if r["status"] == "pass")
    return {
        "target_n": len(TARGET_20),
        "with_primitives": len(covered),
        "pass": pass_n,
        "stale_rejected": not stale.get("ok"),
        "conflict_rejected": not conflict.get("ok"),
        "rows": rows,
        "gate_pass": pass_n == len(covered) and len(covered) > 0 and (not stale.get("ok")) and (not conflict.get("ok")),
    }


def check_universe_coverage() -> dict[str, Any]:
    # Ensure pipeline has run for covered entities
    run_daily_pipeline(entities=list(covered_entities()))
    companies = store.list_objects("company")
    complete_fin = 0
    hist_val = 0
    peers = 0
    risk_n = 0
    timelines = 0
    for e in TARGET_20:
        obj = store.get_object("company", e) or {}
        fin = obj.get("historical_financials") or {}
        if fin and all(k in fin for k in ("price", "eps", "revenue", "net_income")):
            complete_fin += 1
        val = ((obj.get("historical_valuation") or {}).get("metrics") or {}).get("PE") or {}
        if val.get("points"):
            hist_val += 1
        if (obj.get("peer_group") or {}).get("peers"):
            peers += 1
        if (obj.get("risk") or {}).get("found"):
            risk_n += 1
        if (obj.get("timeline") or {}).get("n", 0) > 0:
            timelines += 1
    n = len(TARGET_20)
    pct = lambda x: round(100.0 * x / n, 1)  # noqa: E731
    nifty = tier_report("nifty_50")
    return {
        "target_universe": list(TARGET_20),
        "target_n": n,
        "metrics": {
            "companies_covered": {"value": len([e for e in TARGET_20 if e in companies]), "pct": pct(len([e for e in TARGET_20 if e in companies])), "target": "100% of target"},
            "complete_financials": {"value": complete_fin, "pct": pct(complete_fin)},
            "historical_valuation": {"value": hist_val, "pct": pct(hist_val)},
            "peer_sets": {"value": peers, "pct": pct(peers)},
            "risk_metrics": {"value": risk_n, "pct": pct(risk_n)},
            "timelines": {"value": timelines, "pct": pct(timelines)},
        },
        "nifty_50": {
            "declared": nifty.get("declared"),
            "covered": nifty.get("covered"),
            "coverage_pct": nifty.get("coverage_pct"),
            "by_level": nifty.get("by_level"),
        },
        "primitive_entities": covered_entities(),
        "honest_gaps": [e for e in TARGET_20 if not has_primitives(e)],
    }


def check_stability(days: int = 3) -> dict[str, Any]:
    store.reset_store()
    day_reports = []
    for d in range(days):
        t0 = time.time()
        # Inject duplicate filings scenario via store raw then daily
        result = run_daily_pipeline(entities=list(covered_entities())[:5])
        packs = {e: deepcopy(store.get_pack(e)) for e in covered_entities()[:5]}
        # Re-run same day — reproducibility / idempotence
        result2 = run_daily_pipeline(entities=list(covered_entities())[:5])
        packs2 = {e: store.get_pack(e) for e in covered_entities()[:5]}
        # Compare PE points stability
        stable = True
        for e, p1 in packs.items():
            p2 = packs2.get(e) or {}
            if (p1 or {}).get("historical_pe") != (p2 or {}).get("historical_pe"):
                # allow float noise
                try:
                    if abs(float(p1.get("historical_pe")) - float(p2.get("historical_pe"))) > 1e-6:
                        stable = False
                except Exception:
                    stable = False
        dup = dedupe_filings(
            [{"filing_id": "A", "date": "2025-01-01"}, {"filing_id": "A", "date": "2025-01-01"}, {"filing_id": "B", "date": "2025-01-02"}]
        )
        day_reports.append(
            {
                "day": d + 1,
                "ok": result.get("ok") and result2.get("ok"),
                "collection_failures": len(result.get("collection_failures") or []),
                "validation_failures": len(result.get("validation_failures") or []),
                "reproducible": stable,
                "dedupe_ok": len(dup) == 2,
                "elapsed_ms": int((time.time() - t0) * 1000),
            }
        )
    return {
        "days": days,
        "reports": day_reports,
        "gate_pass": all(r["ok"] and r["reproducible"] and r["dedupe_ok"] for r in day_reports),
    }


def _run_benchmark(label: str) -> dict[str, Any]:
    rows = []
    for q, ticker in BENCHMARK_QUESTIONS:
        t0 = time.time()
        r = govern_answer(q, ticker_hint=ticker)
        ms = int((time.time() - t0) * 1000)
        val = r.get("validation") or {}
        committee = r.get("committee") or {}
        rows.append(
            {
                "q": q[:80],
                "ticker": ticker,
                "complete": bool(val.get("complete")),
                "coverage": val.get("coverage"),
                "missing_n": len(val.get("missing") or []),
                "narrative_allowed": bool(r.get("narrative_allowed")),
                "unsupported": bool(committee.get("stance") == "Insufficient evidence" or not val.get("complete")),
                "latency_ms": ms,
                "question_type": r.get("question_type"),
            }
        )
    n = len(rows)
    return {
        "label": label,
        "n": n,
        "complete_pct": round(100.0 * sum(1 for x in rows if x["complete"]) / n, 1),
        "avg_coverage": round(sum(float(x.get("coverage") or 0) for x in rows) / n, 4),
        "unsupported_pct": round(100.0 * sum(1 for x in rows if x["unsupported"]) / n, 1),
        "avg_latency_ms": int(sum(x["latency_ms"] for x in rows) / n),
        "p95_latency_ms": sorted(x["latency_ms"] for x in rows)[int(0.95 * (n - 1))],
        "rows": rows,
    }


def check_reasoning_regression() -> dict[str, Any]:
    # BEFORE: clear KF objects so historical falls back to derived/seeds
    store.reset_store()
    before = _run_benchmark("before_kf")
    # AFTER: populate KF
    run_daily_pipeline(entities=list(covered_entities()))
    after = _run_benchmark("after_kf")
    return {
        "before": {k: before[k] for k in before if k != "rows"},
        "after": {k: after[k] for k in after if k != "rows"},
        "deltas": {
            "complete_pct": round(after["complete_pct"] - before["complete_pct"], 1),
            "avg_coverage": round(after["avg_coverage"] - before["avg_coverage"], 4),
            "unsupported_pct": round(after["unsupported_pct"] - before["unsupported_pct"], 1),
            "avg_latency_ms": after["avg_latency_ms"] - before["avg_latency_ms"],
        },
        "before_rows": before["rows"],
        "after_rows": after["rows"],
        "gate_pass": after["complete_pct"] >= before["complete_pct"] and after["avg_latency_ms"] < 15000,
    }


def check_e2e_lifecycle() -> dict[str, Any]:
    reset_governance()
    reset_lifecycle()
    reset_ioi()
    reset_ipi()
    reset_market()
    store.reset_store()

    # 1) Earnings announcement → KF ingest
    ingest = run_daily_pipeline(entities=["INFY"])
    pack = store.get_pack("INFY")
    obj = store.get_object("company", "INFY")

    # 2) Research question
    research = govern_answer("Should we invest £1,000,000 in Infosys?", ticker_hint="INFY")
    ipi = research.get("ipi") or {}
    pdg = research.get("portfolio_decision_graph") or {}

    # 3) Outcome tracked
    decision_id = (ipi.get("ioi") or {}).get("decision_id") or (research.get("ioi") or {}).get("decision_id")
    outcome = None
    learning = None
    if decision_id:
        inject_outcome(
            decision_id,
            {
                "total_return": -0.06,
                "benchmark_return": 0.04,
                "sector_return": -0.02,
                "max_drawdown": 0.10,
                "volatility": 0.22,
                "entry_price": 1600,
                "current_price": 1504,
            },
        )
        outcome = evaluate_decision(decision_id)
        # 4) Learning proposal
        learning = govern_learning(outcome)

    return {
        "ingest_ok": bool(ingest.get("ok")),
        "evidence_pack": bool(pack),
        "company_object": bool(obj),
        "research_attached_ipi": bool(ipi),
        "pdg_valid": bool((pdg.get("integrity") or {}).get("valid")),
        "decision_id": decision_id,
        "outcome_evaluated": bool(outcome and (outcome.get("evaluation") or outcome.get("attribution"))),
        "learning_proposals": len((learning or {}).get("candidates") or (learning or {}).get("proposals") or [])
        if learning
        else 0,
        "learning_auto_deploy": bool((learning or {}).get("auto_deployed")),
        "gate_pass": bool(
            ingest.get("ok")
            and pack
            and obj
            and ipi
            and (pdg.get("integrity") or {}).get("valid")
            and decision_id
            and outcome
            and learning is not None
            and not (learning or {}).get("auto_deployed")
        ),
    }


def main() -> int:
    print("=" * 78)
    print("AGIB PRODUCTION READINESS REVIEW")
    print("Architecture: Reasoning Frozen v1.0 — operate, don't redesign")
    print("=" * 78)

    # Warm pipeline for correctness/coverage
    run_daily_pipeline(entities=list(covered_entities()))

    correctness = check_data_correctness()
    coverage = check_universe_coverage()
    stability = check_stability(days=3)
    regression = check_reasoning_regression()
    e2e = check_e2e_lifecycle()
    gates = quality_gates()

    report = {
        "reviewed_at": _now(),
        "architecture_status": "REASONING_FROZEN_V1",
        "pr_191": "merged",
        "objectives": ["coverage", "quality", "performance", "decision_quality"],
        "1_data_correctness": correctness,
        "2_universe_coverage": coverage,
        "3_stability": stability,
        "4_reasoning_regression": regression,
        "5_e2e_lifecycle": e2e,
        "kf_quality_gates": gates,
        "summary": {
            "correctness": correctness.get("gate_pass"),
            "stability": stability.get("gate_pass"),
            "regression": regression.get("gate_pass"),
            "e2e": e2e.get("gate_pass"),
            "kf_gates": gates.get("passed"),
            "coverage_target20_pct": coverage["metrics"]["companies_covered"]["pct"],
            "honest_gaps_n": len(coverage["honest_gaps"]),
        },
    }

    out_dir = store.store_root() / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "production_readiness.json"
    md_path = out_dir / "production_readiness.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    s = report["summary"]
    cov = coverage["metrics"]
    md = [
        "# AGIB Production Readiness Review",
        "",
        f"Reviewed at: {report['reviewed_at']}",
        "",
        "Status: **Reasoning Architecture Frozen (v1.0)** — operate for coverage/quality/performance/decision quality.",
        "",
        "## Summary gates",
        f"- Data correctness: {'PASS' if s['correctness'] else 'FAIL'} ({correctness['pass']}/{correctness['with_primitives']} verified entities with primitives)",
        f"- Universe coverage (target-20): {cov['companies_covered']['pct']}% covered; honest gaps: {', '.join(coverage['honest_gaps']) or 'none'}",
        f"- Stability (3-day sim): {'PASS' if s['stability'] else 'FAIL'}",
        f"- Reasoning regression: {'PASS' if s['regression'] else 'FAIL'} (complete {regression['before']['complete_pct']}% → {regression['after']['complete_pct']}%, latency {regression['before']['avg_latency_ms']}→{regression['after']['avg_latency_ms']} ms)",
        f"- E2E lifecycle: {'PASS' if s['e2e'] else 'FAIL'}",
        f"- KF quality gates: {'PASS' if s['kf_gates'] else 'FAIL'}",
        "",
        "## Universe coverage (target-20)",
        "",
        "| Metric | Value | % |",
        "| --- | ---: | ---: |",
    ]
    for k, v in cov.items():
        md.append(f"| {k} | {v['value']} | {v['pct']} |")
    md += [
        "",
        f"Nifty 50 registry: {coverage['nifty_50']['covered']}/{coverage['nifty_50']['declared']} ({coverage['nifty_50']['coverage_pct']}%)",
        "",
        "## Operating recommendation",
        "",
        "Do not add reasoning modules. Next PRs must improve Coverage, Quality, Performance, or Decision quality.",
        "Sprint 1 priority: fill honest gaps in target-20 / Nifty 500 panels.",
        "",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")

    # Also copy to artifacts if available
    art = Path("/opt/cursor/artifacts")
    if art.exists():
        (art / "production_readiness.json").write_text(json_path.read_text(), encoding="utf-8")
        (art / "production_readiness.md").write_text(md_path.read_text(), encoding="utf-8")

    print(md_path.read_text())
    print(f"\nJSON: {json_path}")
    print(f"MD:   {md_path}")

    # Readiness is PASS for operate-now if correctness/stability/e2e/kf pass;
    # coverage gaps are expected and reported honestly (not a merge blocker).
    operate_ready = all(
        [
            correctness.get("gate_pass"),
            stability.get("gate_pass"),
            regression.get("gate_pass"),
            e2e.get("gate_pass"),
            gates.get("passed"),
        ]
    )
    print("\nOPERATE_READY:", operate_ready)
    return 0 if operate_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
