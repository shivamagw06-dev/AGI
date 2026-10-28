"""Company knowledge quality engine."""

from __future__ import annotations

from app.aoi.models import CompanyQualityScore
from app.aoi.registry import CompanyRegistry
from app.aoi.sources_config import EXPECTED_DOC_TYPES_PER_COMPANY
from app.aoi.store import AoiStore


def score_company(store: AoiStore, registry: CompanyRegistry, company_id: str) -> CompanyQualityScore:
    co = registry.get(company_id)
    arts = [a for a in store.artifacts.values() if a.company_id == company_id and a.status != "failed"]
    facts = [f for f in store.facts.values() if f.company_id == company_id]
    doc_types = {a.doc_type for a in arts}
    expected = set(EXPECTED_DOC_TYPES_PER_COMPANY)
    missing = expected - doc_types
    coverage = len(doc_types & expected) / max(1, len(expected))
    missing_documents = 1.0 - (len(missing) / max(1, len(expected)))
    freshness = 1.0 if arts else 0.2
    if arts:
        # Prefer recently downloaded
        freshness = 0.85 + 0.15 * min(1.0, len(arts) / 6.0)
    completeness = min(1.0, len(facts) / 8.0)
    confs = [float(f.confidence) for f in facts]
    confidence = sum(confs) / len(confs) if confs else 0.3
    validation = 0.9 if facts else 0.4
    extraction_quality = min(1.0, 0.4 + 0.1 * len({f.field for f in facts}))
    overall = round(
        100
        * (
            0.2 * coverage
            + 0.15 * freshness
            + 0.15 * completeness
            + 0.2 * confidence
            + 0.1 * validation
            + 0.1 * missing_documents
            + 0.1 * extraction_quality
        ),
        2,
    )
    score = CompanyQualityScore(
        company_id=company_id,
        nse_symbol=co.nse_symbol if co else "",
        coverage=round(coverage, 4),
        freshness=round(freshness, 4),
        completeness=round(completeness, 4),
        confidence=round(confidence, 4),
        validation=round(validation, 4),
        missing_documents=round(missing_documents, 4),
        extraction_quality=round(extraction_quality, 4),
        overall=overall,
    )
    store.quality[company_id] = score
    return score


def score_all(store: AoiStore, registry: CompanyRegistry) -> list[CompanyQualityScore]:
    return [score_company(store, registry, co.company_id) for co in registry.nifty50()]
