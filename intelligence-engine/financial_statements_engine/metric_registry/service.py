"""Metric Registry service — single naming authority for AGIB financial metrics."""

from __future__ import annotations

from typing import Any, Iterable

from financial_statements_engine.metric_registry.dictionary import (
    APPENDIX_A_METRICS,
    CANONICAL_METRICS,
    metrics_by_category,
)
from financial_statements_engine.metric_registry.schema import ALLOWED_SCALES, REGISTRY_VERSION
from financial_statements_engine.metric_registry.synonyms import SYNONYMS


class MetricRegistryError(ValueError):
    pass


def list_metrics(*, category: str | None = None, appendix_only: bool = False) -> list[dict[str, Any]]:
    rows = []
    for metric, rec in sorted(CANONICAL_METRICS.items()):
        if appendix_only and not rec.get("appendix_a"):
            continue
        if category and rec.get("category") != category:
            continue
        rows.append(dict(rec))
    return rows


def get_metric(metric: str) -> dict[str, Any] | None:
    rec = CANONICAL_METRICS.get(metric)
    return dict(rec) if rec else None


def is_canonical(metric: str | None) -> bool:
    return bool(metric) and str(metric) in CANONICAL_METRICS


def assert_canonical(metric: str) -> str:
    if not is_canonical(metric):
        raise MetricRegistryError(f"non_canonical_metric: {metric}")
    return metric


def resolve(name: str | None) -> str | None:
    """Resolve extractor/legacy/display name to canonical metric, or None."""
    if not name:
        return None
    key = str(name).strip()
    if not key:
        return None
    if key in CANONICAL_METRICS:
        return key
    if key in SYNONYMS:
        return SYNONYMS[key]
    # case-insensitive synonym / canonical pass
    lower_map = {k.lower(): v for k, v in SYNONYMS.items()}
    if key.lower() in lower_map:
        return lower_map[key.lower()]
    lower_canonical = {m.lower(): m for m in CANONICAL_METRICS}
    return lower_canonical.get(key.lower())


def resolve_required(name: str) -> str:
    canon = resolve(name)
    if not canon:
        raise MetricRegistryError(f"unmapped_metric_name: {name}")
    return canon


def assert_unique_canonical(names: Iterable[str] | None = None) -> None:
    seq = list(names if names is not None else CANONICAL_METRICS.keys())
    if len(seq) != len(set(seq)):
        raise MetricRegistryError("duplicate canonical metrics in registry")


def to_normalized_value(reported_value: float | int | None, scale: str | None) -> float | None:
    if reported_value is None:
        return None
    s = (scale or "ones").lower()
    mult = {
        "ones": 1.0,
        "absolute": 1.0,
        "thousands": 1_000.0,
        "lakhs": 100_000.0,
        "crores": 10_000_000.0,
        "millions": 1_000_000.0,
        "billions": 1_000_000_000.0,
    }.get(s)
    if mult is None:
        return None
    return float(reported_value) * mult


def validate_scale(scale: str | None) -> bool:
    if not scale:
        return False
    return str(scale).lower() in ALLOWED_SCALES or str(scale).lower() == "absolute"


def manifest() -> dict[str, Any]:
    assert_unique_canonical()
    return {
        "registry_version": REGISTRY_VERSION,
        "canonical_count": len(CANONICAL_METRICS),
        "appendix_a_count": len(APPENDIX_A_METRICS),
        "synonym_count": len(SYNONYMS),
        "categories": metrics_by_category(),
        "appendix_a": list(APPENDIX_A_METRICS),
    }
