"""ACS production facade."""

from __future__ import annotations

from typing import Any

from academy.certification.gate import certification_gate
from academy.certification.runner import all_exams, inventory, run_certification, run_exam
from academy.certification.schema import ACS_VERSION, LEVELS


def is_enabled() -> bool:
    try:
        from app.core.config import get_settings

        s = get_settings()
        return bool(getattr(s, "academy", True)) and bool(
            getattr(s, "academy_certification_suite", True)
        )
    except Exception:
        return True


def dashboard() -> dict[str, Any]:
    inv = inventory()
    # sampled gate for dashboard responsiveness
    gate = certification_gate(full=False, limit_per_analyst=5)
    return {
        "programme": "AGI_ACADEMY_CERTIFICATION_SUITE",
        "version": ACS_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "objective": "Certify whether AGI has actually LEARNED — reasoning quality, not ingest",
        "levels": LEVELS,
        "inventory": inv,
        "gate": {
            "allow_merge": gate.get("allow_merge"),
            "overall_intelligence": gate.get("overall_intelligence"),
            "grade": gate.get("grade"),
            "message": gate.get("message"),
        },
        "no_redesign": [
            "engine",
            "ui",
            "provider",
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
        ],
    }


def certify(*, full: bool = False, limit_per_analyst: int | None = 8) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "version": ACS_VERSION}
    suite = run_certification(limit_per_analyst=None if full else limit_per_analyst)
    gate = {
        "allow_merge": suite["certificate"]["certified"],
        "overall_intelligence": suite["certificate"]["overall_intelligence"],
        "grade": suite["certificate"]["grade"],
    }
    return {**suite, "enabled": True, "gate": gate}


def quality_gates(*, full: bool = False) -> dict[str, Any]:
    gate = certification_gate(full=full, limit_per_analyst=None if full else 8)
    counts = inventory()["counts"]
    checks = {
        "enabled": is_enabled(),
        "business_exams_50": counts.get("business", 0) >= 50,
        "financial_exams_50": counts.get("financial", 0) >= 50,
        "valuation_exams_50": counts.get("valuation", 0) >= 50,
        "sector_exams_40": counts.get("sector", 0) >= 40,
        "macro_exams_40": counts.get("macro", 0) >= 40,
        "risk_exams_40": counts.get("risk", 0) >= 40,
        "management_exams_30": counts.get("management", 0) >= 30,
        "ownership_exams_30": counts.get("ownership", 0) >= 30,
        "certification_pass": bool(gate.get("allow_merge")),
        "overall_ge_80": float(gate.get("overall_intelligence") or 0) >= 80,
        "no_book_metric": True,
    }
    levels_present = set(inventory()["levels"])
    checks["has_core_levels"] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17} <= levels_present
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "gate": gate,
        "version": ACS_VERSION,
    }


def list_inventory() -> dict[str, Any]:
    return {"enabled": is_enabled(), **inventory(), "exam_count": len(all_exams())}


def run_one(exam_id: str) -> dict[str, Any]:
    for e in all_exams():
        if e.exam_id == exam_id:
            return run_exam(e)
    return {"ok": False, "reason": "unknown_exam", "exam_id": exam_id}
