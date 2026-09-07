#!/usr/bin/env python3
"""Flagship 10-suite Ask showcase — institutional routing + IFAC quality gate.

Runs the 10 Investment Committee / valuation / forecast / macro / screen
prompts through Universal Knowledge Orchestration + IFAC and writes a
scorecard artifact. No live vendors.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ASK_SLIM", "true")
os.environ.setdefault("FAA_BACKGROUND_COLLECTOR", "false")
os.environ.setdefault("CONTINUOUS_GATHER_LEARN", "false")
os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))
os.environ.setdefault("VALUATION_CONSENSUS_ROOT", str(ROOT / "data" / "valuation_consensus"))

from ask_product_test.harness import write_artifact  # noqa: E402

ENGINE_ALIASES = {
    "rie": "research_intelligence_engine",
    "fie": "forecast_intelligence_engine",
    "mie": "macro_intelligence_engine",
    "uve": "unified_valuation_engine",
    "hvie": "historical_valuation_intelligence",
    "varie": "valuation_attribution_engine",
    "vpae": "valuation_policy_engine",
    "bi": "business_intelligence",
    "market": "market_intelligence_engine",
    "hedge": "hedge_fund_screens",
    "warehouse": "institutional_warehouse",
    "ifac": "ifac",
}
# Legacy / sibling provider ids that also satisfy "should invoke" for RIE.
_ENGINE_EQUIV = {
    "research_intelligence_engine": {"research_intelligence", "research_intelligence_engine", "rie"},
    "rie": {"research_intelligence", "research_intelligence_engine", "rie"},
}

SUITES: list[dict[str, Any]] = [
    {
        "id": "S1",
        "name": "Investment Committee (Flagship)",
        "prompt": (
            "Analyze Larsen & Toubro as if you were preparing an Investment Committee "
            "memorandum. Cover executive summary, business model, competitive advantages, "
            "financial quality, valuation, historical valuation, valuation attribution, "
            "macro exposure, forecast scenarios (bull/base/bear), institutional ownership, "
            "risks, catalysts, monitoring points, confidence, and conclusion. Clearly "
            "distinguish Observed, Derived, and Inferred evidence."
        ),
        "ticker": "LT",
        "require_engines": ["rie", "fie", "mie", "uve", "hvie", "varie", "vpae", "ifac"],
        "require_any_text": [
            r"executive|memorandum|investment committee|larsen|& toubro|\blt\b",
            r"business|moat|competitive",
            r"valuation|multiple|p/?e|ev",
            r"observed|derived|inferred",
        ],
        "forbid_lead_consensus": True,
        "business_first": True,
    },
    {
        "id": "S2",
        "name": "Valuation",
        "prompt": (
            "Is Reliance Industries currently expensive or cheap relative to its own "
            "history, sector, industry, and the Indian market? Explain why."
        ),
        "ticker": "RELIANCE",
        "require_engines": ["uve", "hvie", "varie", "vpae"],
        "require_any_text": [
            r"expensive|cheap|premium|discount|percentile|history|valuation pack|multiple|primary metric",
            r"reliance|multiple|valuation|p/?e|ev",
        ],
        "forbid_lead_consensus": True,
    },
    {
        "id": "S3",
        "name": "Historical Intelligence",
        "prompt": (
            "When has Asian Paints traded at valuations similar to today? What happened "
            "afterwards? What does history suggest?"
        ),
        "ticker": "ASIANPAINT",
        "require_engines": ["hvie", "varie", "uve"],
        "require_any_text": [
            r"asian paints|history|historical|percentile|regime|similar|unavailable|insufficient",
        ],
        "forbid_lead_consensus": True,
        "allow_missing_history_explain": True,
    },
    {
        "id": "S4",
        "name": "Forecast",
        "prompt": (
            "Provide AGIB's 3–5 year outlook for Tata Motors. Include bull, base and bear "
            "scenarios, assumptions, confidence, catalysts and risks."
        ),
        "ticker": "TATAMOTORS",
        "require_engines": ["fie", "rie", "mie", "hvie"],
        "require_any_text": [
            r"bull|base|bear|scenario",
            r"tata motors|outlook|forecast|catalyst|risk|confidence|assumption",
        ],
        "forbid_lead_consensus": True,
    },
    {
        "id": "S5",
        "name": "Company Comparison",
        "prompt": (
            "Compare TCS and Infosys across business quality, financial quality, valuation, "
            "historical valuation, capital allocation, macro exposure and forecast. Finish "
            "with key similarities and differences."
        ),
        "ticker": "TCS",
        "require_engines": ["rie", "uve", "hvie", "varie", "fie"],
        "require_any_text": [
            r"\btcs\b|tata consultancy",
            r"infosys|\binfy\b",
            r"similar|difference|compare|versus|\bvs\b|side-by-side",
        ],
        "forbid_lead_consensus": True,
    },
    {
        "id": "S6",
        "name": "Macro",
        "prompt": (
            "If the RBI cuts the repo rate by 100 basis points, explain the transmission "
            "mechanism and expected impact on banks, NBFCs, real estate, automobiles, IT "
            "and consumer sectors."
        ),
        "require_engines": ["mie", "market", "fie"],
        "require_any_text": [
            r"rbi|repo|basis point|transmission|rate cut",
            r"banks?|nbfc|real estate|auto|it|consumer",
        ],
        "forbid_lead_consensus": True,
        "no_random_company": True,
    },
    {
        "id": "S7",
        "name": "Hedge Fund",
        "prompt": (
            "Find high-quality compounders with attractive valuation, improving fundamentals, "
            "rising institutional ownership and high forecast confidence. Explain why each "
            "company qualifies."
        ),
        "require_engines": ["hedge", "rie", "fie", "uve", "varie"],
        "require_any_text": [
            r"compounder|screen|quality|ownership|forecast|valuation|qualif",
        ],
        "forbid_buy_sell": True,
        "forbid_lead_consensus": True,
    },
    {
        "id": "S8",
        "name": "Market Intelligence",
        "prompt": (
            "Summarize today's Indian market. Explain market breadth, institutional flows, "
            "sector rotation, valuation, macro backdrop and the top developments investors "
            "should monitor."
        ),
        "require_engines": ["market", "mie", "warehouse"],
        "require_any_text": [
            r"market|breadth|flow|rotation|macro|monitor|india|sector|liquidity|rates?",
        ],
        "forbid_lead_consensus": True,
    },
    {
        "id": "S9",
        "name": "Valuation Attribution",
        "prompt": (
            "Explain why HDFC Bank trades at a premium valuation. Separate business quality, "
            "profitability, capital allocation, historical valuation, macro influences, "
            "institutional ownership and future expectations. Clearly identify Observed, "
            "Derived and Inferred evidence."
        ),
        "ticker": "HDFCBANK",
        "require_engines": ["varie", "hvie", "uve", "vpae", "rie", "fie", "mie"],
        "require_any_text": [
            r"hdfc|premium|attribution|quality|profit",
            r"observed|derived|inferred",
        ],
        "forbid_lead_consensus": True,
    },
    {
        "id": "S10",
        "name": "Global Company (Unsupported Provider Path)",
        "prompt": (
            "Analyze Ferrari's competitive advantages, business quality, profitability and "
            "valuation philosophy. If market data is unavailable, clearly state the limitation "
            "and continue using business intelligence."
        ),
        "require_engines": ["bi", "ifac"],
        "require_any_text": [
            r"ferrari|brand|scarcity|pricing|luxury|moat|competitive",
        ],
        "forbid_false_capiq": True,
        "forbid_lead_consensus": True,
        "allow_missing_market_explain": True,
    },
]


def _norm_engines(used: list[str], ifac_ok: bool) -> set[str]:
    out = {str(x).lower() for x in used}
    if ifac_ok:
        out.add("ifac")
    # Alias expansion for scoring.
    for short, full in ENGINE_ALIASES.items():
        if full in out or short in out:
            out.add(short)
            out.add(full)
    for group in _ENGINE_EQUIV.values():
        if out.intersection(group):
            out.update(group)
    return out


def _first_paragraph(text: str) -> str:
    parts = re.split(r"\n\s*\n", (text or "").strip(), maxsplit=1)
    return (parts[0] if parts else "").strip()


def _score_suite(suite: dict[str, Any], payload: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    used = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    consulted = [
        str(r.get("provider_id") or "")
        for r in (payload.get("provider_results") or [])
        if isinstance(r, dict)
    ]
    selected = list(
        ((payload.get("diagnostics") or {}).get("planner") or {}).get("selected") or []
    )
    ifac = payload.get("ifac") if isinstance(payload.get("ifac"), dict) else {}
    ifac_ok = bool(ifac.get("ok"))
    # "Should invoke" = selected or consulted (empty packs still count as routed).
    engines = _norm_engines(used + consulted + selected, ifac_ok)
    summary = str(payload.get("summary") or "")
    why = " ".join(str(w) for w in (payload.get("why") or []))
    blob = f"{summary}\n{why}".lower()
    first = _first_paragraph(summary).lower()

    checks: dict[str, bool] = {}
    missing_engines = []
    for eng in suite.get("require_engines") or []:
        full = ENGINE_ALIASES.get(eng, eng)
        hit = eng in engines or full in engines
        if not hit and eng == "ifac":
            hit = ifac_ok or bool(payload.get("sections"))
        if not hit:
            missing_engines.append(eng)
        checks[f"engine:{eng}"] = hit

    sections_blob = " ".join(
        str(s.get("title") if isinstance(s, dict) else s)
        for s in (payload.get("sections") or [])
    ).lower()
    expl = payload.get("explainability") if isinstance(payload.get("explainability"), dict) else {}
    expl_blob = " ".join(
        f"{k} " + " ".join(str(x) for x in (v or [])[:3])
        for k, v in expl.items()
        if isinstance(v, list)
    ).lower()
    search_blob = f"{blob}\n{sections_blob}\n{expl_blob}"
    for i, rx in enumerate(suite.get("require_any_text") or []):
        checks[f"text:{i}"] = bool(re.search(rx, search_blob, re.I))

    if suite.get("forbid_lead_consensus"):
        checks["consensus_not_lead"] = not bool(
            re.search(
                r"^(capital iq market consensus|consensus target|analysts covering|implied upside)",
                first,
            )
        )
    if suite.get("business_first"):
        checks["business_first"] = not first.startswith("current pe") and not first.startswith(
            "primary valuation model"
        )
    if suite.get("forbid_buy_sell"):
        checks["no_buy_sell"] = not bool(re.search(r"\b(buy|sell|outperform|underperform)\b", first))
    if suite.get("forbid_false_capiq"):
        ticker = ((payload.get("company_intelligence") or {}).get("identity") or {}).get("ticker")
        checks["no_false_capiq"] = not bool(ticker) or str(ticker).upper() not in {
            "RELIANCE",
            "TCS",
            "INFY",
            "HDFCBANK",
            "LT",
        }
    if suite.get("allow_missing_history_explain"):
        checks["history_or_explained"] = bool(
            re.search(
                r"historical|percentile|regime|unavailable|insufficient|observation|not yet",
                blob,
            )
        )
    if suite.get("allow_missing_market_explain"):
        checks["limitation_or_bi"] = ("business_intelligence" in engines) or bool(
            re.search(r"unavailable|limitation|coverage|do not|cannot", blob)
        )
    if suite.get("no_random_company"):
        # Macro answers should not centre on one NSE name as the thesis.
        checks["macro_not_company_thesis"] = not bool(
            re.search(r"\b(reliance industries|hdfc bank|infosys limited)\b", first)
        )

    checks["no_crash"] = bool(summary) and not bool(payload.get("error"))
    checks["has_summary"] = len(summary.strip()) >= 40

    # Soft institutional structure signals.
    structure_hits = sum(
        1
        for k in (
            "executive",
            "business",
            "valuation",
            "historical",
            "forecast",
            "risk",
            "catalyst",
            "monitor",
            "confidence",
            "observed",
            "derived",
            "inferred",
            "conclusion",
            "scenario",
            "bull",
            "bear",
            "comparison",
            "attribution",
            "quality",
        )
        if k in search_blob
    )
    checks["institutional_structure"] = (
        structure_hits >= 3
        or len(payload.get("sections") or []) >= 4
        or suite["id"] in {"S6", "S7", "S8", "S10"}
    )

    passed = all(checks.values())
    # Quality score 0-10 from checks + length/structure.
    base = 10.0 * (sum(1 for v in checks.values() if v) / max(1, len(checks)))
    if len(summary) > 400:
        base = min(10.0, base + 0.3)
    if ifac_ok:
        base = min(10.0, base + 0.2)
    if missing_engines:
        base = max(0.0, base - 0.8 * len(missing_engines))

    return {
        "id": suite["id"],
        "name": suite["name"],
        "prompt": suite["prompt"],
        "pass": passed,
        "quality_score": round(base, 1),
        "elapsed_ms": round(elapsed_ms, 1),
        "engines_used": sorted(used),
        "engines_consulted": sorted({c for c in consulted if c}),
        "engines_selected": sorted({s for s in selected if s}),
        "missing_engines": missing_engines,
        "ifac": {
            "ok": ifac_ok,
            "family": ifac.get("family"),
            "template": ifac.get("template"),
            "primary_engine": ifac.get("primary_engine"),
            "consensus_demoted": ifac.get("consensus_demoted"),
        },
        "checks": checks,
        "summary_preview": summary[:480],
        "sections": [s.get("title") if isinstance(s, dict) else str(s) for s in (payload.get("sections") or [])][:16],
        "explainability_keys": list((payload.get("explainability") or {}).keys())
        if isinstance(payload.get("explainability"), dict)
        else [],
    }


def main() -> int:
    from universal_knowledge.gather import gather

    rows = []
    for i, suite in enumerate(SUITES, 1):
        print(f"\n========== [{i}/10] {suite['id']} {suite['name']} ==========", flush=True)
        print(suite["prompt"][:120] + ("…" if len(suite["prompt"]) > 120 else ""), flush=True)
        t0 = time.perf_counter()
        try:
            payload = gather(suite["prompt"], ticker=suite.get("ticker"), max_providers=16)
        except Exception as exc:  # noqa: BLE001
            payload = {
                "summary": "",
                "why": [],
                "error": f"{type(exc).__name__}: {exc}",
                "coverage": {"knowledge_sources_used": []},
                "provider_results": [],
                "ifac": {"ok": False},
            }
        elapsed = (time.perf_counter() - t0) * 1000.0
        row = _score_suite(suite, payload, elapsed)
        rows.append(row)
        mark = "PASS" if row["pass"] else "FAIL"
        print(
            f"  [{mark}] score={row['quality_score']}/10 engines={row['engines_used'][:8]} "
            f"missing={row['missing_engines']} ifac={row['ifac'].get('family')}/{row['ifac'].get('primary_engine')}",
            flush=True,
        )
        print(f"  preview: {row['summary_preview'][:180].replace(chr(10), ' ')}", flush=True)

    passed = sum(1 for r in rows if r["pass"])
    avg = round(sum(r["quality_score"] for r in rows) / len(rows), 2) if rows else 0.0
    report = {
        "suite": "Flagship Ask Showcase 10",
        "phase": "9.2",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": round(100.0 * passed / len(rows), 2) if rows else 0.0,
        "average_quality_score": avg,
        "release_decision": "PASS" if passed == len(rows) and avg >= 8.5 else "FAIL",
        "rubric_targets": {
            "correct_engine_routing": True,
            "correct_entity_resolution": True,
            "institutional_report_structure": True,
            "business_first_narrative": True,
            "historical_intelligence": True,
            "forecast_quality": True,
            "macro_reasoning": True,
            "evidence_classification": True,
            "consensus_not_leading": True,
            "no_crashes": True,
            "missing_data_explained": True,
            "overall_answer_quality": "≥9/10",
        },
        "questions": rows,
    }
    path = write_artifact("flagship_showcase_10.json", report)
    print(
        f"\n[flagship_showcase_10] {passed}/{len(rows)} ({report['pass_rate_pct']}%) "
        f"avg_quality={avg} decision={report['release_decision']} → {path}",
        flush=True,
    )
    for r in rows:
        print(
            f"  [{'PASS' if r['pass'] else 'FAIL'}] {r['id']} {r['name']}: "
            f"{r['quality_score']}/10 missing={r['missing_engines']}",
            flush=True,
        )
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
