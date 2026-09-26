"""Module 10 — Institutional Judgement Suite (IES expansion).

Cross-framework and cross-author reasoning cases.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.iki.applicability import explain_dcf_for_entity
from institutional_reasoning.iki.graph_relations import author_conflicts
from institutional_reasoning.iki.schema import IKI_VERSION, PHASE3_TARGETS

IJS_VERSION = "institutional-judgement-suite-v1.0.0"


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "ijs_001",
            "question": "Should DCF be used for HDFC Bank?",
            "kind": "dcf_bank",
            "entity_id": "HDFCBANK",
        },
        {
            "case_id": "ijs_002",
            "question": "Value Zomato.",
            "kind": "value_zomato",
            "entity_id": "ZOMATO",
        },
        {
            "case_id": "ijs_003",
            "question": "Compare Buffett and Damodaran on Zomato.",
            "kind": "author_conflict",
            "entity_id": "ZOMATO",
            "authors": ("Buffett", "Damodaran"),
        },
        {
            "case_id": "ijs_004",
            "question": "Why is DCF wrong for banks?",
            "kind": "dcf_banks_why",
            "entity_id": "HDFCBANK",
        },
        {
            "case_id": "ijs_005",
            "question": "Is DCF applicable for Nifty IT?",
            "kind": "dcf_index",
            "entity_id": "NIFTYIT",
        },
        {
            "case_id": "ijs_006",
            "question": "Which framework dominates for Infosys valuation?",
            "kind": "dominance",
            "entity_id": "INFY",
        },
        {
            "case_id": "ijs_007",
            "question": "Why would Buffett reject Zomato?",
            "kind": "buffett_reject",
            "entity_id": "ZOMATO",
        },
        {
            "case_id": "ijs_008",
            "question": "Compare Graham vs Damodaran on Infosys.",
            "kind": "graham_vs_damodaran",
            "entity_id": "INFY",
            "authors": ("Graham", "Damodaran"),
        },
        {
            "case_id": "ijs_009",
            "question": "Which evidence invalidates DCF for HDFC Bank?",
            "kind": "invalidate_dcf",
            "entity_id": "HDFCBANK",
        },
        {
            "case_id": "ijs_010",
            "question": "Explain disagreement between relative valuation and Graham on Zomato.",
            "kind": "explain_disagreement",
            "entity_id": "ZOMATO",
        },
    ]


def _grade(case: dict[str, Any]) -> dict[str, Any]:
    kind = case["kind"]
    failures: list[str] = []
    record = govern_answer(case["question"], ticker_hint=case.get("entity_id"))
    iki = record.get("iki") or {}
    applicability = (iki.get("applicability") or {})
    debate = iki.get("debate") or {}
    frameworks = {f["framework_id"]: f for f in (record.get("frameworks") or [])}

    if kind in {"dcf_bank", "dcf_banks_why", "invalidate_dcf"}:
        expl = explain_dcf_for_entity(case["entity_id"], "Company")
        if expl.get("applicability") != "No":
            failures.append("expected DCF applicability No")
        if "financial" not in str(expl.get("reason") or "").lower() and "bank" not in str(
            expl.get("reason") or ""
        ).lower():
            failures.append(f"reason unclear: {expl.get('reason')}")
        if expl.get("alternative") != "residual_income":
            failures.append(f"expected residual_income alt, got {expl.get('alternative')}")
        dcf = frameworks.get("dcf_applicability") or frameworks.get("dcf_fcff")
        if dcf and dcf.get("status") not in {"not_applicable", "insufficient_evidence"}:
            # pre-rejected path may mark not_applicable
            if not (iki.get("execution_order") or []):
                failures.append("DCF should not execute as primary for banks")

    elif kind == "dcf_index":
        dcf = frameworks.get("dcf_applicability")
        if not dcf or dcf.get("status") != "not_applicable":
            failures.append("DCF must be not_applicable for index")

    elif kind == "value_zomato":
        # Relative should be preferred; Graham rejected; DCF low confidence / conditional
        scores = {s["framework_id"]: s for s in (applicability.get("scores") or [])}
        rel = scores.get("rel_val_damodaran") or {}
        graham = scores.get("margin_of_safety") or scores.get("graham_net_net") or {}
        if not rel.get("applicable"):
            failures.append("relative valuation should apply to Zomato")
        if graham.get("applicable"):
            failures.append("Graham should be rejected for Zomato")
        authors = (debate.get("authors") or {})
        if (authors.get("Graham") or {}).get("stance") != "rejects":
            failures.append("Graham mental model should reject Zomato")
        if "domin" not in str(debate.get("resolution") or "").lower():
            failures.append("committee resolution missing dominance statement")

    elif kind in {"author_conflict", "graham_vs_damodaran", "explain_disagreement"}:
        authors = case.get("authors") or ("Buffett", "Damodaran")
        conf = author_conflicts(authors[0], authors[1])
        if kind == "graham_vs_damodaran":
            conf = author_conflicts("Graham", "Damodaran")
        if not conf.get("conflicts") and not (debate.get("conflicts") or []):
            # debate conflicts from mental models are enough
            if not debate.get("conflicts"):
                failures.append("expected explained author/framework conflict")
        if debate.get("conflicts"):
            if not all(c.get("explanation") for c in debate["conflicts"]):
                failures.append("conflict missing explanation")
            if not all(c.get("evidence_shown") for c in debate["conflicts"]):
                failures.append("conflict missing evidence_shown")

    elif kind == "dominance":
        if not debate.get("dominant_framework"):
            failures.append("missing dominant framework")
        if not debate.get("resolution"):
            failures.append("missing resolution")

    elif kind == "buffett_reject":
        authors = (debate.get("authors") or {})
        if (authors.get("Buffett") or {}).get("stance") != "rejects":
            failures.append("Buffett should reject Zomato")

    return {
        "case_id": case["case_id"],
        "kind": kind,
        "question": case["question"],
        "passed": not failures,
        "failures": failures,
        "dominant_framework": debate.get("dominant_framework"),
        "resolution": debate.get("resolution"),
        "conflicts": len(debate.get("conflicts") or []),
    }


def run_judgement_suite() -> dict[str, Any]:
    results = [_grade(c) for c in _cases()]
    passed = sum(1 for r in results if r["passed"])
    score = round(100.0 * passed / max(1, len(results)), 2)
    gate = {
        "overall_judgement": score >= PHASE3_TARGETS["overall_judgement"],
        "conflict_cases_explained": all(
            r["passed"]
            for r in results
            if r["kind"] in {"author_conflict", "graham_vs_damodaran", "explain_disagreement"}
        ),
        "dcf_bank_correct": all(
            r["passed"] for r in results if r["kind"] in {"dcf_bank", "dcf_banks_why", "invalidate_dcf"}
        ),
    }
    return {
        "suite": "Institutional Judgement Suite",
        "version": IJS_VERSION,
        "iki_version": IKI_VERSION,
        "n": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "score": score,
        "targets": PHASE3_TARGETS,
        "phase3_gate": {"checks": gate, "passed": all(gate.values())},
        "results": results,
    }
