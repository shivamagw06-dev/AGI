"""Validation finding helpers."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.schema import SEVERITIES


def finding(
    *,
    rule_id: str,
    rule_name: str,
    status: str,
    severity: str,
    evidence: Any = None,
    affected_metrics: list[str] | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise ValueError(f"invalid_severity: {severity}")
    if status not in ("PASS", "FAIL", "SKIP", "WARN"):
        raise ValueError(f"invalid_status: {status}")
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "status": status,
        "severity": severity,
        "evidence": evidence,
        "affected_metrics": list(affected_metrics or []),
        "detail": detail,
    }


def extract_metrics(draft: dict[str, Any]) -> dict[str, Any]:
    """Flatten canonical metrics from a parse draft. Never invents values."""
    mapped = (draft.get("mapped") or {}).get("metrics") or {}
    out: dict[str, Any] = {}
    for k, v in mapped.items():
        if isinstance(v, dict):
            val = v.get("normalized_value")
            if val is None:
                val = v.get("reported_value")
            out[str(k)] = {
                "value": val,
                "reported_value": v.get("reported_value"),
                "normalized_value": v.get("normalized_value"),
                "source_field": v.get("source_field"),
                "statement_type": (v.get("metric_record") or {}).get("statement_type"),
            }
        else:
            out[str(k)] = {"value": v}

    # Also absorb facts from drafts[] if present
    for d in draft.get("drafts") or []:
        for fact in d.get("facts") or []:
            m = str(fact.get("metric") or "")
            if not m or m in out:
                continue
            out[m] = {
                "value": fact.get("normalized_value")
                if fact.get("normalized_value") is not None
                else fact.get("reported_value"),
                "reported_value": fact.get("reported_value"),
                "normalized_value": fact.get("normalized_value"),
                "statement_type": fact.get("statement_type"),
                "fact_id": fact.get("fact_id"),
            }
    return out


def metric_value(metrics: dict[str, Any], key: str) -> float | None:
    row = metrics.get(key)
    if row is None:
        return None
    if isinstance(row, dict):
        v = row.get("value")
        if v is None:
            v = row.get("normalized_value")
        if v is None:
            v = row.get("reported_value")
        return float(v) if isinstance(v, (int, float)) else None
    if isinstance(row, (int, float)):
        return float(row)
    return None


def close(a: float | None, b: float | None, tol: float) -> bool:
    if a is None or b is None:
        return True  # missing ⇒ skip identity (not fail)
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tol
