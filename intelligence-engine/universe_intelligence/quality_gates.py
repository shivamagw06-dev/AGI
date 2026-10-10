"""Institutional quality gates — one failure ⇒ not institutional-ready."""

from __future__ import annotations

from typing import Any

from universe_intelligence.schema import QUALITY_GATES


def institutional_quality_gates(ticker: str) -> dict[str, Any]:
    """PASS/FAIL gates. Coverage = YES only when all gates PASS."""
    e = ticker.upper()
    gates: dict[str, str] = {g: "FAIL" for g in QUALITY_GATES}
    reasons: dict[str, str] = {}

    try:
        from knowledge_factory.institutional_depth import institutional_depth_checklist, acceptance_for_company
        from knowledge_factory.coverage import _company_checklist

        depth = institutional_depth_checklist(e)
        checks = depth.get("checks") or {}
        base = _company_checklist(e)
        bchecks = base.get("checks") or {}
        acc = acceptance_for_company(e)
        tests = acc.get("tests") or {}

        def _set(name: str, ok: bool, reason: str) -> None:
            gates[name] = "PASS" if ok else "FAIL"
            if not ok:
                reasons[name] = reason

        _set("identity", bool(checks.get("identity")), "identity_incomplete")
        _set("historical", bool(checks.get("historical_financials") and checks.get("historical_valuation")), "historical_depth_incomplete")
        _set(
            "accounting",
            bool(checks.get("derived_metrics")),
            "financial_intelligence_incomplete",
        )
        _set("sector", bool(checks.get("sector_links")), "sector_links_missing")
        _set("macro", bool(checks.get("macro_links")), "macro_links_missing")
        _set("risk", bool(bchecks.get("risk")), "risk_series_missing")
        _set(
            "evidence",
            bool(checks.get("evidence_pack") and depth.get("evidence_quality_ok")),
            "evidence_pack_or_quality_fail",
        )
        _set("replay", bool(tests.get("historical_replay")), "historical_replay_fail")
        _set("decision", bool(checks.get("decision_readiness")), "decision_not_ready")
    except Exception as exc:
        reasons["system"] = f"gate_eval_error:{exc}"

    passed = sum(1 for v in gates.values() if v == "PASS")
    institutional_ready = all(v == "PASS" for v in gates.values())
    return {
        "ticker": e,
        "gates": gates,
        "reasons": reasons,
        "passed": passed,
        "total": len(QUALITY_GATES),
        "institutional_ready": institutional_ready,
        "institutional_coverage": institutional_ready,  # one failure ⇒ Coverage NO
        "rule": "One FAIL ⇒ Institutional Coverage = NO",
        "fabricated": False,
    }
