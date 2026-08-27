"""Final Production Acceptance certification report."""

from __future__ import annotations

from collections import Counter
from typing import Any

from institutional_acceptance.schema import (
    AGIB_PLATFORM_VERSION,
    CERTIFICATION_LABEL,
    PAT_PRODUCT,
    PAT_VERSION,
    PAT_WORKSTREAM_ID,
    PHASES,
    SUCCESS_CRITERIA,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def build_certification_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(c.get("status", "FAIL") for c in cases)
    total = len(cases)
    passed = counts.get("PASS", 0)
    failed = counts.get("FAIL", 0)
    skipped = counts.get("SKIP", 0)
    critical_failures = sum(
        1 for c in cases if c.get("status") == "FAIL" and c.get("critical")
    )
    pass_rate = (100.0 * passed / total) if total else 0.0

    by_phase: dict[str, dict[str, Any]] = {}
    for code, key, title in PHASES:
        phase_cases = [c for c in cases if c.get("phase") == key]
        pc = Counter(c.get("status", "FAIL") for c in phase_cases)
        p_pass = pc.get("PASS", 0)
        p_total = len(phase_cases)
        by_phase[key] = {
            "code": code,
            "title": title,
            "total": p_total,
            "pass": p_pass,
            "fail": pc.get("FAIL", 0),
            "skip": pc.get("SKIP", 0),
            "status": "PASS"
            if p_total and pc.get("FAIL", 0) == 0
            else ("EMPTY" if not p_total else "FAIL"),
        }

    arch_score = 100
    for c in cases:
        if c.get("id") == "P12-score-100":
            arch_score = int((c.get("meta") or {}).get("architecture_score") or (100 if c.get("status") == "PASS" else 0))
            break

    security_violations = sum(
        1
        for c in cases
        if c.get("phase") == "security" and c.get("status") == "FAIL"
    )
    memory_leaks = sum(
        1
        for c in cases
        if c.get("id") == "P15-memory-leaks-zero" and c.get("status") == "FAIL"
    )

    criteria = {
        "test_cases": total >= SUCCESS_CRITERIA["min_test_cases"],
        "pass_rate": pass_rate >= SUCCESS_CRITERIA["pass_rate_pct"] and failed == 0,
        "critical_failures": critical_failures <= SUCCESS_CRITERIA["critical_failures"],
        "architecture_score": arch_score >= SUCCESS_CRITERIA["architecture_score"],
        "memory_leaks": memory_leaks <= SUCCESS_CRITERIA["memory_leaks"],
        "security_violations": security_violations <= SUCCESS_CRITERIA["security_violations"],
    }
    certified = all(criteria.values()) and failed == 0

    phase_lines = []
    for _code, key, title in PHASES:
        row = by_phase.get(key) or {}
        phase_lines.append(f"{title}: {row.get('status', 'EMPTY')}")

    text = "\n".join(
        [
            "AGIB Production Acceptance Test",
            "",
            "Version:",
            f"v{AGIB_PLATFORM_VERSION} GA",
            "",
            "System Tests:",
            f"{passed}/{total} PASS",
            "",
            "Architecture:",
            by_phase.get("rc01", {}).get("status", "EMPTY"),
            "",
            "Security:",
            by_phase.get("security", {}).get("status", "EMPTY"),
            "",
            "Performance:",
            by_phase.get("performance", {}).get("status", "EMPTY"),
            "",
            "Observability:",
            by_phase.get("observability", {}).get("status", "EMPTY"),
            "",
            "Knowledge Graph:",
            by_phase.get("knowledge_graph", {}).get("status", "EMPTY"),
            "",
            "Ask AGI:",
            by_phase.get("ask_agi", {}).get("status", "EMPTY"),
            "",
            "Workspace:",
            by_phase.get("research_workspace", {}).get("status", "EMPTY"),
            "",
            "Publishing:",
            by_phase.get("publishing", {}).get("status", "EMPTY"),
            "",
            "Multi Portfolio:",
            by_phase.get("multi_portfolio", {}).get("status", "EMPTY"),
            "",
            "Stress:",
            by_phase.get("performance", {}).get("status", "EMPTY"),
            "",
            "Failure Recovery:",
            by_phase.get("failure_injection", {}).get("status", "EMPTY"),
            "",
            "24-Hour Stability:",
            by_phase.get("long_running_stability", {}).get("status", "EMPTY"),
            "",
            "Overall Result",
            "",
            CERTIFICATION_LABEL if certified else "NOT CERTIFIED",
        ]
    )

    return {
        "workstream_id": PAT_WORKSTREAM_ID,
        "product": PAT_PRODUCT,
        "version": PAT_VERSION,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "as_of": now_iso(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate_pct": round(pass_rate, 2),
        "critical_failures": critical_failures,
        "architecture_score": arch_score,
        "security_violations": security_violations,
        "memory_leaks": memory_leaks,
        "criteria": criteria,
        "phases": by_phase,
        "phase_summary": phase_lines,
        "certified": certified,
        "overall_result": CERTIFICATION_LABEL if certified else "NOT CERTIFIED",
        "report_text": text,
        "failures": [c for c in cases if c.get("status") == "FAIL"][:50],
    }
