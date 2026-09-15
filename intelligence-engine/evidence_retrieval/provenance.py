"""Provenance helpers for retrieval traces."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.store import utc_now


def retrieval_provenance(*, engine: str = "iere") -> dict[str, Any]:
    return {
        "source": engine,
        "retrieved_at": utc_now(),
        "validated_at": utc_now(),
        "collector": "evidence_retrieval",
        "version": "iere-v1",
        "fabricated": False,
        "bypassed_knowledge_factory": False,
        "queried_raw_api": False,
    }
