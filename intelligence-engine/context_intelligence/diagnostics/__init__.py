"""CIE diagnostics for admin / IRS."""

from __future__ import annotations

from typing import Any


def diagnose(row: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not row.get("time_context", {}).get("time_horizon"):
        issues.append("missing_time_horizon")
    if not row.get("research_context_card"):
        issues.append("missing_research_context_card")
    if row.get("executed_layers"):
        issues.append("illegal_layer_execution")
    conf = (row.get("confidence") or {}).get("overall")
    if conf is not None and float(conf) < 0.85:
        issues.append("low_context_confidence")
    return {
        "ok": not issues,
        "issues": issues,
        "runtime_ms": row.get("runtime_ms"),
        "missing_context": row.get("missing_context") or [],
        "ignored_context": row.get("ignored_context") or [],
    }
