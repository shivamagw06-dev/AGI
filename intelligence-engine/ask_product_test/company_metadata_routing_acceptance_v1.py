"""Company Metadata Routing Acceptance.

Metadata questions ("Axis Bank primary sector") must be answered from the
Capital IQ registry and must never reach Entity Intelligence, the Unknown
Entity Policy, KUL, fusion or the composer.

Target: 100% routing accuracy, zero metadata queries reaching KUL or Unknown
Entity, and zero analytical questions hijacked by the router.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUITE_VERSION = "1.0.0"

# (question, expected field, expected value or None to only require an answer)
METADATA_CASES: tuple[tuple[str, str, str | None], ...] = (
    ("Axis Bank primary sector", "primary_sector", "Financials"),
    ("Infosys primary sector", "primary_sector", "Information Technology"),
    ("Reliance primary sector", "primary_sector", "Energy"),
    ("Titan primary sector", "primary_sector", "Consumer Discretionary"),
    ("NTPC primary sector", "primary_sector", "Utilities"),
    ("HDFC Bank primary sector", "primary_sector", "Financials"),
    ("ICICI Bank sector", "primary_sector", "Financials"),
    ("TCS primary sector", "primary_sector", "Information Technology"),
    ("Wipro sector", "primary_sector", "Information Technology"),
    ("HCLTech sector", "primary_sector", "Information Technology"),
    ("Sun Pharmaceutical Industries sector", "primary_sector", "Health Care"),
    ("Apollo Hospitals primary sector", "primary_sector", "Health Care"),
    ("Maruti Suzuki sector", "primary_sector", "Consumer Discretionary"),
    ("Trent sector", "primary_sector", "Consumer Discretionary"),
    ("ITC primary sector", "primary_sector", "Consumer Staples"),
    ("Nestle India sector", "primary_sector", "Consumer Staples"),
    ("DMart sector", "primary_sector", "Consumer Staples"),
    ("UltraTech Cement sector", "primary_sector", "Materials"),
    ("JSW Steel primary sector", "primary_sector", "Materials"),
    ("Tata Steel sector", "primary_sector", "Materials"),
    ("Asian Paints sector", "primary_sector", "Materials"),
    ("Larsen & Toubro sector", "primary_sector", "Industrials"),
    ("InterGlobe Aviation sector", "primary_sector", "Industrials"),
    ("Power Grid sector", "primary_sector", "Utilities"),
    ("DLF primary sector", "primary_sector", "Real Estate"),
    ("Bharti Airtel primary sector", "primary_sector", "Communication Services"),
    ("ONGC primary sector", "primary_sector", "Energy"),
    ("BPCL sector", "primary_sector", "Energy"),
    ("Axis Bank primary industry", "primary_industry", "Diversified Banks"),
    ("Infosys industry", "primary_industry", "IT Consulting and Other Services"),
    ("ONGC industry", "primary_industry", "Integrated Oil and Gas"),
    ("Apollo Hospitals industry", "primary_industry", "Health Care Facilities"),
    ("InterGlobe Aviation industry", "primary_industry", "Passenger Airlines"),
    ("Axis Bank business type", "business_type", "Universal Bank"),
    ("Infosys business type", "business_type", "IT Services"),
    ("ICICI Bank ticker", "ticker", "ICICIBANK"),
    ("TCS ticker", "ticker", "TCS"),
    ("Infosys website", "website", None),
    ("NTPC country", "country", None),
    ("Apollo Hospitals parent", "parent", None),
)

# Questions that must NOT be captured by the metadata router.
ANALYTICAL_CASES: tuple[str, ...] = (
    "Why does Axis Bank have a strong moat?",
    "What is Axis Bank's investment thesis?",
    "Compare Infosys and TCS margins",
    "Explain enterprise value",
    "What is the consensus target price for Infosys?",
    "How should Apollo Hospitals be valued?",
    "What drives valuation for banks?",
    "Which companies have the highest consensus upside?",
    "Explain the business model of Reliance Industries",
    "What are the biggest risks for IndiGo?",
)

# Ambiguous or uncovered names must fall through, never bind a namesake.
FALLTHROUGH_CASES: tuple[str, ...] = (
    "Apollo sector",
    "HDFC sector",
    "Tata sector",
    "Sun Pharma industry",
    "Air India sector",
    "Quorvex Analytics sector",
)


def _route(question: str):
    from company_identity.metadata_router import route

    return route(question)


def evaluate() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for question, field, expected in METADATA_CASES:
        failed: list[str] = []
        hit = _route(question)
        if not hit:
            failed.append("not_routed_to_metadata")
        else:
            fields = {f["field"]: f["value"] for f in hit.get("fields") or []}
            if field not in fields:
                if field in {f.lower() for f in (hit.get("missing_fields") or [])}:
                    failed.append("field_missing_in_registry")
                else:
                    failed.append(f"field_not_answered:{field}")
            elif expected is not None and str(fields[field]) != expected:
                failed.append(f"wrong_value:{fields[field]}!={expected}")
        results.append(
            {
                "kind": "metadata",
                "question": question,
                "passed": not failed,
                "failed": failed,
                "answer": (hit or {}).get("summary"),
            }
        )

    for question in ANALYTICAL_CASES:
        hit = _route(question)
        results.append(
            {
                "kind": "analytical",
                "question": question,
                "passed": hit is None,
                "failed": [] if hit is None else ["hijacked_by_metadata_router"],
                "answer": (hit or {}).get("summary"),
            }
        )

    for question in FALLTHROUGH_CASES:
        hit = _route(question)
        results.append(
            {
                "kind": "fallthrough",
                "question": question,
                "passed": hit is None,
                "failed": [] if hit is None else [f"bound_namesake:{hit.get('ticker')}"],
                "answer": (hit or {}).get("summary"),
            }
        )

    return results_to_report(results)


def evaluate_pipeline() -> list[dict[str, Any]]:
    """End-to-end: metadata questions must not reach EI / unknown entity / KUL."""
    from app.ui.service import UiService

    svc = UiService()
    checks: list[dict[str, Any]] = []
    for question, _field, expected in METADATA_CASES[:12]:
        failed: list[str] = []
        try:
            view = svc.search(question)
        except Exception as exc:
            checks.append(
                {
                    "kind": "pipeline",
                    "question": question,
                    "passed": False,
                    "failed": [f"ask_error:{type(exc).__name__}"],
                    "answer": None,
                }
            )
            continue
        intent = str(getattr(view, "intent", "") or "")
        sources = list(getattr(getattr(view, "meta", None), "sources", []) or [])
        summary = str(getattr(view, "executive_summary", "") or "")
        if intent != "company_metadata":
            failed.append(f"wrong_intent:{intent}")
        if sources != ["company_identity"]:
            failed.append(f"wrong_sources:{sources}")
        if "could not verify" in summary.lower():
            failed.append("unknown_entity_refusal")
        if expected and expected not in summary:
            failed.append("expected_value_missing")
        checks.append(
            {
                "kind": "pipeline",
                "question": question,
                "passed": not failed,
                "failed": failed,
                "answer": summary[:120],
            }
        )
    return checks


def results_to_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    by_kind: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_kind.setdefault(r["kind"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += 1 if r["passed"] else 0
    pass_rate = round((passed / total) * 100.0, 2) if total else 0.0
    return {
        "suite": "company_metadata_routing_acceptance_v1",
        "version": SUITE_VERSION,
        "total": total,
        "passed": passed,
        "pass_rate_pct": pass_rate,
        "by_kind": by_kind,
        "decision": "PASS" if pass_rate == 100.0 else "FAIL",
        "results": results,
    }


def run(*, include_pipeline: bool = True) -> dict[str, Any]:
    try:
        from ask_product_test.acceptance_data import _load_vc_rows, MINIMUM_REQUIRED

        if len(_load_vc_rows()) < MINIMUM_REQUIRED["valuation_consensus_rows"]:
            return {
                "suite": "company_metadata_routing_acceptance_v1",
                "version": SUITE_VERSION,
                "total": 0,
                "passed": 0,
                "pass_rate_pct": None,
                "by_kind": {},
                "decision": "NOT_EVALUATED",
                "failure_class": "INFRASTRUCTURE",
                "reason": "Acceptance dataset unavailable — valuation consensus has insufficient rows.",
                "results": [],
            }
    except Exception:
        pass

    report = evaluate()
    results = list(report["results"])
    if include_pipeline:
        results.extend(evaluate_pipeline())
    return results_to_report(results)
