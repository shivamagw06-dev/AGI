"""Analog search façade — delegates to retrieval engine."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.retrieval.engine import retrieve_memories


def search_analogs(**kwargs: Any) -> dict[str, Any]:
    return retrieve_memories(**kwargs)
