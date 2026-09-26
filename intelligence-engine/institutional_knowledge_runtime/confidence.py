"""Deterministic assertion confidence scoring."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.schema import CONFIDENCE_WEIGHTS


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _evidence_quality(evidence_pack: dict[str, Any] | None) -> float:
    if not evidence_pack:
        return 0.0
    supporting = evidence_pack.get("supporting") or []
    if not supporting:
        return 0.0
    scores = [float(e.get("source_quality", 50)) for e in supporting if isinstance(e, dict)]
    return sum(scores) / len(scores) if scores else 0.0


def _evidence_freshness(evidence_pack: dict[str, Any] | None) -> float:
    if not evidence_pack:
        return 0.0
    supporting = evidence_pack.get("supporting") or []
    if not supporting:
        return 0.0
    scores = [float(e.get("freshness", 50)) for e in supporting if isinstance(e, dict)]
    return sum(scores) / len(scores) if scores else 0.0


def _coverage(assertion: dict[str, Any], evidence_pack: dict[str, Any] | None) -> float:
    refs = assertion.get("evidence_refs") or []
    if not refs:
        return 0.0
    if not evidence_pack:
        return 30.0
    resolved = len(evidence_pack.get("supporting") or []) + len(evidence_pack.get("neutral") or [])
    return _clamp(100.0 * resolved / max(len(refs), 1))


def _historical_consistency(assertion: dict[str, Any]) -> float:
    history = assertion.get("history") or []
    if len(history) < 2:
        return 70.0
    statuses = [str(h.get("status") or "") for h in history if isinstance(h, dict)]
    if not statuses:
        return 70.0
    stable = sum(1 for s in statuses if s in {"SUPPORTED", "PARTIAL", "ANSWERED"})
    return _clamp(100.0 * stable / len(statuses))


def _contradiction_penalty(assertion: dict[str, Any], evidence_pack: dict[str, Any] | None) -> float:
    contradictions = assertion.get("contradictions") or []
    contradicting = (evidence_pack or {}).get("contradicting") or []
    count = len(contradictions) + len(contradicting)
    if count == 0:
        return 100.0
    return _clamp(100.0 - count * 25.0)


def _monitoring_health(assertion: dict[str, Any]) -> float:
    monitoring = assertion.get("monitoring")
    if not isinstance(monitoring, dict):
        return 50.0
    status = str(monitoring.get("status") or "unknown").lower()
    if status == "healthy":
        return 100.0
    if status == "breached":
        return 0.0
    return 50.0


def calculate_confidence(
    assertion: dict[str, Any],
    evidence_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return deterministic confidence with formula, inputs, weights, result."""
    status = str(assertion.get("status") or "UNKNOWN")
    if status == "UNKNOWN":
        return {
            "formula": "unknown_assertion",
            "inputs": {"status": status},
            "weights": CONFIDENCE_WEIGHTS,
            "result": 0,
        }

    inputs = {
        "evidence_quality": _evidence_quality(evidence_pack),
        "evidence_freshness": _evidence_freshness(evidence_pack),
        "coverage": _coverage(assertion, evidence_pack),
        "historical_consistency": _historical_consistency(assertion),
        "contradiction_penalty": _contradiction_penalty(assertion, evidence_pack),
        "monitoring_health": _monitoring_health(assertion),
    }

    weighted = sum(inputs[k] * CONFIDENCE_WEIGHTS[k] for k in CONFIDENCE_WEIGHTS)
    result = int(round(_clamp(weighted)))

    return {
        "formula": "weighted_sum(inputs * CONFIDENCE_WEIGHTS)",
        "inputs": {k: round(v, 2) for k, v in inputs.items()},
        "weights": dict(CONFIDENCE_WEIGHTS),
        "result": result,
    }
