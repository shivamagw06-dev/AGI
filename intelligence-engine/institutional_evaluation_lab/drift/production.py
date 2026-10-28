"""Recommendation drift production — compare two Evaluation Lab releases."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from institutional_evaluation_lab.drift.budget import evaluate_budget
from institutional_evaluation_lab.drift.classify import classify_reason
from institutional_evaluation_lab.drift.magnitude import compute_magnitude
from institutional_evaluation_lab.drift.release_notes import build_release_notes, format_release_notes
from institutional_evaluation_lab.drift.review_queue import build_review_queue
from institutional_evaluation_lab.drift.schema import DRIFT_VERSION, PROGRAMME, UNKNOWN_IS_REGRESSION
from institutional_evaluation_lab.golden_universe import store as golden_store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_release(release_id: str) -> dict[str, Any] | None:
    packed = golden_store.load_release_results(release_id)
    if packed and packed.get("rows"):
        return packed
    # Fallback read ticker files
    if not packed:
        return None
    root = Path(packed["results_dir"])
    rows = []
    for t in (packed.get("manifest") or {}).get("tickers") or []:
        path = root / f"{str(t).upper()}.json"
        if path.exists():
            rows.append(json.loads(path.read_text(encoding="utf-8")))
    packed["rows"] = rows
    packed["n"] = len(rows)
    return packed


def _avg(rows: list[dict[str, Any]], field: str) -> float | None:
    vals = []
    for r in rows:
        v = r.get(field)
        if field == "runtime_ms" and v is None:
            v = (r.get("timing") or {}).get("total_ms")
        if v is None:
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def compare_releases(
    *,
    previous_release: str,
    current_release: str,
    governance_failures: int | None = None,
    persist: bool = True,
    hints: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Full drift analysis between two Evaluation Lab result trees.

    Classifies every recommendation change (DATA/MARKET/MODEL/GOVERNANCE/BUGFIX/UNKNOWN),
    computes magnitude across scores, applies drift budget, builds review queue + release notes.
    """
    prev_pack = _load_release(previous_release)
    cur_pack = _load_release(current_release)
    if not prev_pack:
        return {"ok": False, "error": "previous_release_not_found", "previous_release": previous_release}
    if not cur_pack:
        return {"ok": False, "error": "current_release_not_found", "current_release": current_release}

    prev_by = {
        str(r.get("ticker") or "").upper(): r
        for r in (prev_pack.get("rows") or [])
        if r.get("ticker")
    }
    hints = {str(k).upper(): v for k, v in (hints or {}).items()}

    rows: list[dict[str, Any]] = []
    by_reason: dict[str, int] = {k: 0 for k in ("DATA", "MARKET", "MODEL", "GOVERNANCE", "BUGFIX", "UNKNOWN", "NONE")}
    data_readiness_shift = False

    for cur in cur_pack.get("rows") or []:
        t = str(cur.get("ticker") or "").upper()
        prev = prev_by.get(t)
        reason = classify_reason(prev, cur, hint=hints.get(t))
        magnitude = compute_magnitude(prev, cur)
        decision_changed = bool(magnitude["decision"]["changed"])
        by_reason[reason["code"]] = by_reason.get(reason["code"], 0) + 1
        if reason["code"] == "DATA" and (magnitude.get("by_field") or {}).get("recommendation_readiness", {}).get(
            "delta"
        ):
            data_readiness_shift = True

        rows.append(
            {
                "ticker": t,
                "sector": cur.get("sector") or (prev or {}).get("sector"),
                "bucket": cur.get("bucket") or (prev or {}).get("bucket"),
                "previous_decision": (prev or {}).get("decision"),
                "current_decision": cur.get("decision"),
                "decision_changed": decision_changed,
                "reason": reason,
                "reason_code": reason["code"],
                "magnitude": magnitude,
                "previous_release": previous_release,
                "current_release": current_release,
            }
        )

    changed = [r for r in rows if r["decision_changed"]]
    unknown = [r for r in changed if r["reason_code"] == "UNKNOWN"]

    # Governance failures: from Phase 6 report if present, else argument
    gov_fail = governance_failures
    if gov_fail is None:
        phase6_path = Path(cur_pack["results_dir"]) / "_phase6_governance.json"
        if phase6_path.exists():
            try:
                phase6 = json.loads(phase6_path.read_text(encoding="utf-8"))
                gov_fail = int(phase6.get("critical_rule_failures") or 0)
            except Exception:
                gov_fail = 0
        else:
            gov_fail = 0

    prev_rows = prev_pack.get("rows") or []
    cur_rows = cur_pack.get("rows") or []
    budget = evaluate_budget(
        n=len(rows),
        recommendation_changes=len(changed),
        unknown_count=len(unknown),
        governance_failures=int(gov_fail),
        prev_avg_runtime_ms=_avg(prev_rows, "runtime_ms"),
        cur_avg_runtime_ms=_avg(cur_rows, "runtime_ms"),
        prev_avg_readiness=_avg(prev_rows, "recommendation_readiness"),
        cur_avg_readiness=_avg(cur_rows, "recommendation_readiness"),
        data_driven_readiness_shift=data_readiness_shift,
    )

    review = build_review_queue(rows, budget_passed=budget["passed"], budget_breaches=budget["breaches"])

    # Coverage/health from current summary if available
    cur_summary = cur_pack.get("summary") or {}
    coverage = cur_summary.get("coverage") or {}
    health = cur_summary.get("health") or {
        "average_runtime_ms": cur_summary.get("average_runtime_ms"),
        "gate_pass_rate": cur_summary.get("gate_pass_rate"),
    }

    report: dict[str, Any] = {
        "programme": PROGRAMME,
        "version": DRIFT_VERSION,
        "timestamp": _now(),
        "previous_release": previous_release,
        "current_release": current_release,
        "n": len(rows),
        "recommendations_changed": len(changed),
        "expected": len(changed) - len(unknown),
        "unexpected": len(unknown),
        "by_reason_code": by_reason,
        "unknown_is_regression": UNKNOWN_IS_REGRESSION,
        "budget": budget,
        "review_queue": review,
        "coverage": coverage,
        "health": health,
        "governance_failures": int(gov_fail),
        "rows": rows,
        "changed_rows": changed,
        "ok": budget["passed"] and (len(unknown) == 0 if UNKNOWN_IS_REGRESSION else True),
        "note": (
            "UNKNOWN drift is treated as a regression until explained. "
            "Attach operator hints to reclassify when a known cause exists."
        ),
    }
    report["release_notes"] = build_release_notes(report)
    report["release_notes_text"] = format_release_notes(report["release_notes"])

    if persist:
        out_dir = Path(cur_pack["results_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        light = {k: v for k, v in report.items() if k not in {"rows", "changed_rows"}}
        light["changed_sample"] = changed[:30]
        path = out_dir / "_drift_report.json"
        path.write_text(json.dumps(light, indent=2, default=str), encoding="utf-8")
        notes_path = out_dir / "_release_notes.md"
        notes_path.write_text(report["release_notes_text"] + "\n", encoding="utf-8")
        report["report_path"] = str(path)
        report["release_notes_path"] = str(notes_path)

    return report


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": DRIFT_VERSION,
        "reason_codes": list(
            {
                "DATA": "New evidence",
                "MARKET": "Price/valuation",
                "MODEL": "Decision Engine",
                "GOVERNANCE": "Gate/rules",
                "BUGFIX": "Corrected error",
                "UNKNOWN": "Investigate",
            }.keys()
        ),
        "unknown_is_regression": UNKNOWN_IS_REGRESSION,
    }
