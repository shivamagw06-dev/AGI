"""AIP-09 / AIP-10 Research quality + client answer quality scoring."""

from __future__ import annotations

from typing import Any

from app.aip.models import MetricBundle, QualityScore


def score_research_quality(
    *,
    metrics: MetricBundle | None = None,
    evidence_count: int = 0,
    has_reasoning_package: bool = False,
    has_house_view: bool = False,
    contradiction_resolved: bool = False,
) -> QualityScore:
    components: dict[str, float] = {
        "evidence": min(1.0, evidence_count / 5.0),
        "reasoning": 1.0 if has_reasoning_package else 0.0,
        "house_view": 1.0 if has_house_view else 0.35,
        "contradictions": 1.0 if contradiction_resolved else 0.4,
        "calibration": _cal_component(metrics),
        "prediction": _pred_component(metrics),
    }
    score = round(sum(components.values()) / len(components), 4)
    return QualityScore(
        domain="research",
        score=score,
        components=components,
        notes=["AIP-09 research quality scoring", "No engine redesign"],
    )


def score_client_answer_quality(
    *,
    grounded: bool = False,
    cites_evidence: bool = False,
    confidence_stated: bool = False,
    unknowns_stated: bool = False,
    metrics: MetricBundle | None = None,
    answer_chars: int = 0,
) -> QualityScore:
    components: dict[str, float] = {
        "grounded": 1.0 if grounded else 0.0,
        "evidence_cited": 1.0 if cites_evidence else 0.0,
        "confidence_stated": 1.0 if confidence_stated else 0.2,
        "unknowns_stated": 1.0 if unknowns_stated else 0.3,
        "length_ok": 1.0 if 80 <= answer_chars <= 4000 else 0.5,
        "calibration": _cal_component(metrics),
    }
    score = round(sum(components.values()) / len(components), 4)
    return QualityScore(
        domain="client_answer",
        score=score,
        components=components,
        notes=["AIP-10 client answer quality", "Homepage search never answers directly"],
    )


def _cal_component(metrics: MetricBundle | None) -> float:
    if metrics is None or metrics.calibration_error is None:
        return 0.5
    # 0 error → 1.0; 0.5+ error → ~0
    return round(max(0.0, 1.0 - float(metrics.calibration_error) * 2.0), 4)


def _pred_component(metrics: MetricBundle | None) -> float:
    if metrics is None or metrics.prediction_accuracy is None:
        return 0.5
    return round(max(0.0, min(1.0, float(metrics.prediction_accuracy))), 4)


def quality_from_payload(payload: dict[str, Any]) -> QualityScore:
    domain = str(payload.get("domain") or "research")
    if domain == "client_answer":
        return score_client_answer_quality(
            grounded=bool(payload.get("grounded")),
            cites_evidence=bool(payload.get("cites_evidence")),
            confidence_stated=bool(payload.get("confidence_stated")),
            unknowns_stated=bool(payload.get("unknowns_stated")),
            answer_chars=int(payload.get("answer_chars") or 0),
        )
    return score_research_quality(
        evidence_count=int(payload.get("evidence_count") or 0),
        has_reasoning_package=bool(payload.get("has_reasoning_package")),
        has_house_view=bool(payload.get("has_house_view")),
        contradiction_resolved=bool(payload.get("contradiction_resolved")),
    )
