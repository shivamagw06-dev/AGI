"""Immutable Alternative Data dataset registry objects."""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence.provenance import provenance
from knowledge_factory.alternative_data_intelligence.schema import IADI_VERSION, UNKNOWN


def build_dataset(
    *,
    dataset_id: str,
    name: str,
    provider: str,
    description: str,
    frequency: str,
    coverage: str,
    first_available: str | None,
    latest_available: str | None,
    quality: str = "phase_1_seed",
    confidence: float = 0.85,
    source: str,
    collector: str = "iadi.registry",
    company_links: list[str] | None = None,
    industry_links: list[str] | None = None,
    sector_links: list[str] | None = None,
    macro_links: list[str] | None = None,
    government_links: list[str] | None = None,
    domain: str | None = None,
    unit: str | None = None,
    notes: str | None = None,
    observation_count: int = 0,
    institutional_ready: bool = False,
    trends: dict[str, Any] | None = None,
) -> dict[str, Any]:
    did = str(dataset_id or "").lower()
    if not did:
        raise ValueError("dataset_id required")
    if not provider or not source:
        raise ValueError("provider and source required")

    return {
        "dataset_id": did,
        "dataset": did,
        "name": name,
        "provider": provider,
        "description": description,
        "domain": domain,
        "frequency": frequency,
        "coverage": coverage,
        "unit": unit,
        "first_available": first_available or UNKNOWN,
        "latest_available": latest_available or UNKNOWN,
        "quality": quality,
        "confidence": round(float(confidence), 4),
        "validation": {"status": "pending"},
        "provenance": provenance(
            source=source,
            collector=collector,
            confidence=confidence,
            derived_from=[f"registry:{did}"],
        ),
        "company_links": list(company_links or []),
        "industry_links": list(industry_links or []),
        "sector_links": list(sector_links or []),
        "macro_links": list(macro_links or []),
        "government_links": list(government_links or []),
        "observation_count": observation_count,
        "trends": trends or {},
        "notes": notes,
        "version": IADI_VERSION,
        "fabricated": False,
        "immutable": True,
        "institutional_ready": institutional_ready,
        "phase": "phase_1",
    }
