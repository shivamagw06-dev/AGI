"""Institutional Evidence Retrieval Engine (IERE)."""

from evidence_retrieval.pipeline import retrieve_evidence
from evidence_retrieval.production import company, dashboard, health, replay, search
from evidence_retrieval.schema import IERE_VERSION, MODULE_CODE, PROGRAMME

__all__ = [
    "IERE_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "retrieve_evidence",
    "search",
    "company",
    "dashboard",
    "health",
    "replay",
]
