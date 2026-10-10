"""FSE-02.3 — Official Source Registry & multi-source collection layer.

Additive adapters feed ``collection.ingest.ingest`` only.
"""

from financial_statements_engine.collection.source_layer.collect import collect_and_ingest
from financial_statements_engine.collection.source_layer.fallback import collect_with_fallback
from financial_statements_engine.collection.source_layer.registry import (
    list_registrations,
    registry_manifest,
    select_sources,
)

__all__ = [
    "collect_and_ingest",
    "collect_with_fallback",
    "list_registrations",
    "registry_manifest",
    "select_sources",
]
