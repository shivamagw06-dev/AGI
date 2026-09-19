"""Knowledge quality scoring for corpus objects (Phase 10)."""

from __future__ import annotations

from typing import Any

from app.kc.models import KnowledgeQualityScore


def _filled(fields: list[Any]) -> int:
    n = 0
    for f in fields:
        if isinstance(f, str) and f.strip():
            n += 1
        elif isinstance(f, (list, dict)) and f:
            n += 1
    return n


def score_company(obj: Any) -> KnowledgeQualityScore:
    d = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else dict(obj)
    meta = d.get("meta") or {}
    profile_fields = [
        d.get("business_description"),
        d.get("products"),
        d.get("segments"),
        d.get("revenue_mix"),
        d.get("geographic_mix"),
        d.get("competitors"),
        d.get("management"),
        d.get("shareholding"),
    ]
    thesis_fields = [
        d.get("latest_thesis"),
        d.get("bull_case"),
        d.get("bear_case"),
        d.get("key_risks"),
        d.get("key_catalysts"),
        d.get("valuation"),
        d.get("historical_house_views"),
        d.get("predictions"),
    ]
    completeness = min(1.0, _filled(profile_fields + thesis_fields) / 12.0)
    confidence = float(meta.get("confidence") or 0.0)
    freshness = float(meta.get("freshness") or 0.0)
    evidence = min(1.0, len(meta.get("document_ids") or []) / 5.0 + (0.2 if d.get("related_research") else 0.0))
    consistency = 0.75
    if d.get("bull_case") and d.get("bear_case"):
        consistency = 0.9
    if d.get("key_risks") and not d.get("latest_thesis"):
        consistency = 0.55
    recency = freshness
    coverage = min(1.0, 0.35 + 0.65 * completeness)
    overall = round(
        0.15 * coverage
        + 0.20 * confidence
        + 0.15 * freshness
        + 0.15 * evidence
        + 0.10 * consistency
        + 0.15 * completeness
        + 0.10 * recency,
        4,
    )
    return KnowledgeQualityScore(
        object_kind="company",
        object_key=str(d.get("ticker") or meta.get("key") or ""),
        coverage_score=round(coverage, 4),
        confidence_score=round(confidence, 4),
        freshness_score=round(freshness, 4),
        evidence_score=round(evidence, 4),
        consistency_score=round(consistency, 4),
        completeness_score=round(completeness, 4),
        recency_score=round(recency, 4),
        overall_quality=overall,
    )


def score_sector(obj: Any) -> KnowledgeQualityScore:
    d = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else dict(obj)
    meta = d.get("meta") or {}
    fields = [
        d.get("definition"),
        d.get("growth_drivers"),
        d.get("demand_drivers"),
        d.get("key_metrics"),
        d.get("major_companies"),
        d.get("valuation_framework"),
        d.get("current_agi_view"),
        d.get("risks"),
        d.get("catalysts"),
        d.get("latest_thesis"),
    ]
    completeness = min(1.0, _filled(fields) / 8.0)
    confidence = float(meta.get("confidence") or 0.0)
    freshness = float(meta.get("freshness") or 0.0)
    evidence = 0.4 + (0.3 if d.get("latest_thesis") else 0.0) + (0.3 if d.get("current_agi_view") else 0.0)
    consistency = 0.85 if d.get("risks") and d.get("catalysts") else 0.6
    overall = round(
        0.15 * completeness
        + 0.2 * confidence
        + 0.15 * freshness
        + 0.15 * min(1.0, evidence)
        + 0.1 * consistency
        + 0.15 * completeness
        + 0.1 * freshness,
        4,
    )
    return KnowledgeQualityScore(
        object_kind="sector",
        object_key=str(d.get("sector_id") or ""),
        coverage_score=round(completeness, 4),
        confidence_score=round(confidence, 4),
        freshness_score=round(freshness, 4),
        evidence_score=round(min(1.0, evidence), 4),
        consistency_score=round(consistency, 4),
        completeness_score=round(completeness, 4),
        recency_score=round(freshness, 4),
        overall_quality=overall,
    )


def score_theme(obj: Any) -> KnowledgeQualityScore:
    d = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else dict(obj)
    meta = d.get("meta") or {}
    fields = [
        d.get("definition"),
        d.get("investment_thesis"),
        d.get("companies"),
        d.get("risks"),
        d.get("catalysts"),
        d.get("current_agi_view"),
        d.get("macro_drivers"),
    ]
    completeness = min(1.0, _filled(fields) / 6.0)
    confidence = float(meta.get("confidence") or 0.0)
    freshness = float(meta.get("freshness") or 0.0)
    overall = round(0.25 * completeness + 0.25 * confidence + 0.25 * freshness + 0.25 * completeness, 4)
    return KnowledgeQualityScore(
        object_kind="theme",
        object_key=str(d.get("theme_id") or ""),
        coverage_score=round(completeness, 4),
        confidence_score=round(confidence, 4),
        freshness_score=round(freshness, 4),
        evidence_score=round(0.5 + 0.5 * bool(d.get("investment_thesis")), 4),
        consistency_score=0.8,
        completeness_score=round(completeness, 4),
        recency_score=round(freshness, 4),
        overall_quality=overall,
    )


def score_macro(obj: Any) -> KnowledgeQualityScore:
    d = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else dict(obj)
    meta = d.get("meta") or {}
    fields = [
        d.get("definition"),
        d.get("why_investors_care"),
        d.get("leading_indicators"),
        d.get("lagging_indicators"),
        d.get("affected_sectors"),
        d.get("current_agi_view"),
        d.get("historical_episodes"),
    ]
    completeness = min(1.0, _filled(fields) / 6.0)
    confidence = float(meta.get("confidence") or 0.0)
    freshness = float(meta.get("freshness") or 0.0)
    overall = round(0.3 * completeness + 0.3 * confidence + 0.2 * freshness + 0.2 * completeness, 4)
    return KnowledgeQualityScore(
        object_kind="macro",
        object_key=str(d.get("macro_id") or ""),
        coverage_score=round(completeness, 4),
        confidence_score=round(confidence, 4),
        freshness_score=round(freshness, 4),
        evidence_score=round(0.45 + 0.55 * bool(d.get("current_agi_view")), 4),
        consistency_score=0.8,
        completeness_score=round(completeness, 4),
        recency_score=round(freshness, 4),
        overall_quality=overall,
    )


def average_quality(scores: list[KnowledgeQualityScore]) -> float:
    if not scores:
        return 0.0
    return round(sum(s.overall_quality for s in scores) / len(scores), 4)
