"""Monitoring rule evaluation."""

from __future__ import annotations

from typing import Any


def evaluate_monitoring_rule(
    assertion: dict[str, Any],
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate monitoring rules for a single assertion."""
    monitoring = assertion.get("monitoring")
    if not isinstance(monitoring, dict):
        return {"evaluated": False, "status": "unknown", "breached": False}

    trigger = str(monitoring.get("trigger") or "")
    status = str(monitoring.get("status") or "unknown").lower()
    metrics = metrics or {}

    breached = False
    if trigger and metrics:
        # Simple threshold: operating_margin < 22%
        if "operating_margin" in trigger and "operating_margin" in metrics:
            threshold = 22.0
            if "<" in trigger:
                try:
                    threshold = float(trigger.split("<")[-1].strip().replace("%", ""))
                except ValueError:
                    pass
            margin = float(metrics["operating_margin"])
            breached = margin < threshold
            status = "breached" if breached else "healthy"

    return {
        "evaluated": True,
        "assertion_id": assertion.get("assertion_id"),
        "status": status,
        "breached": breached,
        "trigger": trigger or None,
    }


def evaluate_monitoring(
    assertions: list[dict[str, Any]],
    metrics: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate monitoring for all assertions; return updated assertions and reports."""
    reports: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []

    for assertion in assertions:
        report = evaluate_monitoring_rule(assertion, metrics=metrics)
        reports.append(report)
        a = dict(assertion)
        if report.get("evaluated") and report.get("breached"):
            a["status"] = "STALE"
            mon = dict(a.get("monitoring") or {})
            mon["status"] = "breached"
            a["monitoring"] = mon
        updated.append(a)

    return updated, reports


def list_monitoring(iko: dict[str, Any]) -> list[dict[str, Any]]:
    """List active monitoring rules from IKO claims."""
    out: list[dict[str, Any]] = []
    for claim in iko.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        mon = claim.get("monitoring")
        if isinstance(mon, dict) and mon:
            out.append({
                "assertion_id": claim.get("claim_id"),
                "statement": claim.get("statement"),
                "monitoring": mon,
            })
    return out
