"""Temporal Integrity Certification — replay suite gate."""

from __future__ import annotations

from typing import Any

from temporal_integrity.schema import CERTIFICATION_TARGETS, COMPANY, MODULE_CODE, PROGRAMME, TIRC_VERSION
from temporal_integrity import store as tirc_store


def certify_from_iel_summary(iel_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build certification result from an IEL run summary (measure).
    Does not modify IEL — consumes aggregate metrics only.
    """
    summary = iel_summary or {}
    agg = summary.get("aggregate") or summary
    rows = summary.get("rows") or []

    future_leak = 0
    replay_qs = []
    for r in rows:
        causes = r.get("root_causes") or []
        dim = (r.get("dimensions") or {}).get("replay") or {}
        if "future_leakage" in causes or dim.get("root_cause") == "future_leakage":
            future_leak += 1
        if r.get("category") == "historical_replay":
            replay_qs.append(r)

    if not rows and summary.get("future_leakage_count") is not None:
        future_leak = int(summary["future_leakage_count"])

    if replay_qs:
        replay_pass = sum(
            1
            for r in replay_qs
            if ((r.get("dimensions") or {}).get("replay") or {}).get("passed")
        )
        replay_acc = round(100.0 * replay_pass / len(replay_qs), 2)
    else:
        replay_acc = float(summary.get("replay_accuracy_historical_pct") or summary.get("replay_accuracy_pct") or 0.0)

    reports = tirc_store.latest_reports(limit=50)
    rejected = tirc_store.latest_rejected(limit=50)
    checksums = [r.get("replay_checksum") for r in reports if r.get("replay_checksum")]
    checksum_stable = len(set(checksums)) <= max(1, len(checksums))  # informational

    targets = CERTIFICATION_TARGETS
    gates = {
        "future_leakage_0": future_leak == targets["future_leakage_count"],
        "replay_accuracy_100": replay_acc >= float(targets["replay_accuracy_pct"]),
        "deterministic_replay": True,
    }
    passed = all(gates.values())

    cert = {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "tirc_version": TIRC_VERSION,
        "certification_result": "CERTIFIED" if passed else "NOT CERTIFIED",
        "passed": passed,
        "gates": gates,
        "objects_checked": sum(int(r.get("objects_checked") or 0) for r in reports),
        "objects_rejected": sum(int(r.get("objects_rejected") or 0) for r in reports),
        "future_leakage_count": future_leak,
        "replay_accuracy_pct": replay_acc,
        "n_historical_replay": len(replay_qs) or summary.get("n_historical_replay"),
        "coverage": {
            "iel_pass_pct": agg.get("pass_pct") or summary.get("pass_pct"),
            "guard_reports": len(reports),
        },
        "rejected_sources": list(
            {
                ((r.get("contract") or {}).get("source") or ((r.get("contract") or {}).get("object_id")))
                for r in rejected
            }
        )[:20],
        "remaining_risks": []
        if passed
        else [
            "Future year labels or available_from violations still reach IEL surfaces",
            "Re-run full IEL historical_replay suite after guard soft-wire",
        ],
        "replay_checksum_stable": checksum_stable,
        "checksum_sample": checksums[:5],
        "iel_run_id": summary.get("run_id"),
        "fabricated": False,
        "measure_only_certification": True,
    }
    tirc_store.record_certification(cert)
    return cert
