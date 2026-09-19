"""Institutional Documents Intelligence (IDI) — Track 4 evidence layer."""

from knowledge_factory.institutional_documents.pipeline import run_institutional_documents_pipeline
from knowledge_factory.institutional_documents.production import (
    company,
    dashboard,
    health,
    replay,
    report,
    run_pipeline,
    search,
)
from knowledge_factory.institutional_documents.schema import IDI_VERSION, LAYER, PROGRAMME

__all__ = [
    "IDI_VERSION",
    "LAYER",
    "PROGRAMME",
    "run_institutional_documents_pipeline",
    "run_pipeline",
    "health",
    "dashboard",
    "company",
    "report",
    "search",
    "replay",
]
