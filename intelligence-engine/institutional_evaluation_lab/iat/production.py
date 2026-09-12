"""IAT façade — run the Phase 1 Institutional Acceptance Test over a release."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from institutional_evaluation_lab.iat.areas import (
    evaluate_decision_quality,
    evaluate_drift,
    evaluate_evidence,
    evaluate_governance,
    evaluate_operational,
    evaluate_universe,
)
from institutional_evaluation_lab.iat.freeze import freeze_baseline
from institutional_evaluation_lab.iat.report import format_institutional_evaluation_report
from institutional_evaluation_lab.iat.schema import (
    ARCHITECTURE_VERSION,
    IAT_VERSION,
    PROGRAMME,
    SCOPE_LOCKS,
    THRESHOLDS,
)
from institutional_evaluation_lab.observability.loaders import load_release_bundle


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": IAT_VERSION,
        "architecture_version": ARCHITECTURE_VERSION,
        "scope_locks": dict(SCOPE_LOCKS),
        "question": "Is AGIB ready to become the baseline architecture?",
        "thresholds": dict(THRESHOLDS),
        "consumes": [
            "golden_universe_results",
            "phase6_governance",
            "recommendation_drift",
            "release_observability",
        ],
        "acceptance_exam_only": True,
    }


def run_iat(
    *,
    release_id: str,
    previous_release: str | None = None,
    persist: bool = True,
    freeze: bool = False,
    require_full_universe: bool = True,
) -> dict[str, Any]:
    """
    Execute the Institutional Acceptance Test against results/{release_id}.

    Does not re-score companies or alter engines. Consumes Evaluation Lab,
    Phase 6, and Drift artifacts. Freeze is refused unless overall PASS.
    """
    bundle = load_release_bundle(release_id)
    if not bundle.get("found"):
        return {
            "found": False,
            "release_id": release_id,
            "version": IAT_VERSION,
            "error": "release_not_found",
            "overall": {"status": "FAIL", "fail_reasons": ["release_not_found"]},
        }

    rows = list(bundle.get("rows") or [])
    summary = bundle.get("summary") or {}
    phase6 = bundle.get("phase6")
    drift = bundle.get("drift")

    # If drift missing but previous_release provided, leave FAIL (exam requires drift)
    golden_summary = None
    try:
        from knowledge_factory.phase1_golden_test_set import summary as golden_sum

        golden_summary = golden_sum()
    except Exception:
        golden_summary = None

    universe = evaluate_universe(rows, golden_summary=golden_summary)
    if not require_full_universe:
        # Smoke / unit-test mode: universe size check becomes advisory
        universe = {
            **universe,
            "status": "PASS" if rows else "FAIL",
            "advisory": True,
            "note": "require_full_universe=False — composition check advisory only",
        }

    governance = evaluate_governance(rows, phase6)
    evidence = evaluate_evidence(rows, summary)
    decision_quality = evaluate_decision_quality(rows)
    operational = evaluate_operational(rows, summary)
    drift_area = evaluate_drift(drift)

    areas = {
        "universe": universe,
        "governance": governance,
        "evidence": evidence,
        "decision_quality": decision_quality,
        "operational": operational,
        "drift": drift_area,
    }

    fail_reasons: list[str] = []
    for name, block in areas.items():
        if block.get("status") != "PASS":
            fail_reasons.append(f"{name}:{block.get('status')}")

    overall_status = "PASS" if not fail_reasons else "FAIL"
    overall = {
        "status": overall_status,
        "qualifies_as_baseline": overall_status == "PASS",
        "fail_reasons": fail_reasons,
        "question": "Is AGIB ready to become the baseline architecture?",
        "answer": (
            "Yes — AGIB Phase 1 qualifies as the production baseline."
            if overall_status == "PASS"
            else "No — Institutional Acceptance Test did not pass."
        ),
    }

    pack: dict[str, Any] = {
        "found": True,
        "programme": PROGRAMME,
        "version": IAT_VERSION,
        "architecture_version": ARCHITECTURE_VERSION,
        "scope_locks": dict(SCOPE_LOCKS),
        "release_id": release_id,
        "previous_release": previous_release,
        "results_dir": bundle.get("results_dir"),
        "companies_tested": len(rows),
        "thresholds": dict(THRESHOLDS),
        "universe": universe,
        "governance": governance,
        "evidence": evidence,
        "decision_quality": decision_quality,
        "operational": operational,
        "drift": drift_area,
        "overall": overall,
        "acceptance_exam_only": True,
        "note": (
            "Phase 1 IAT — consume-only exam over Golden 200 + Governance + Drift. "
            "Does not modify Decision Engine, Constitution, Governance Spec, or scoring."
        ),
    }
    pack["report_text"] = format_institutional_evaluation_report(pack)

    freeze_result = None
    if freeze:
        freeze_result = freeze_baseline(pack, results_dir=bundle.get("results_dir"))
        pack["freeze"] = freeze_result
    else:
        pack["freeze"] = {
            "frozen": False,
            "refused": overall_status != "PASS",
            "reason": "freeze_not_requested" if overall_status == "PASS" else "IAT_DID_NOT_PASS",
        }

    if persist and bundle.get("results_dir"):
        root = Path(bundle["results_dir"])
        root.mkdir(parents=True, exist_ok=True)
        light = {k: v for k, v in pack.items() if k != "report_text"}
        (root / "_iat_report.json").write_text(json.dumps(light, indent=2, default=str), encoding="utf-8")
        (root / "_iat_report.md").write_text(pack["report_text"] + "\n", encoding="utf-8")
        pack["report_path"] = str(root / "_iat_report.json")
        pack["report_markdown_path"] = str(root / "_iat_report.md")

    return pack
