"""AOI source connectors — pluggable, independent, configuration-driven."""

from app.aoi.connectors.factory import build_connectors, list_optional_connectors

__all__ = ["build_connectors", "list_optional_connectors"]
