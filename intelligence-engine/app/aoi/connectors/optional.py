"""Optional future connectors — designed, not executed in AOI v1 runs."""

from __future__ import annotations

from app.aoi.connector import SourceConnector
from app.aoi.models import DocumentArtifact
from app.aoi.registry import CompanyRegistry
from app.aoi.sources_config import OPTIONAL_CONNECTORS


class OptionalStubConnector(SourceConnector):
    """Placeholder connector for roadmap sources (OSM, weather, satellite, etc.)."""

    category = "optional"

    def __init__(self, connector_id: str, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.connector_id = connector_id
        self.name = name

    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        _ = registry
        return []

    def health_check(self) -> dict:
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "status": "designed_not_implemented",
            "aoi_version_target": "v2+",
        }


def build_optional_stubs() -> list[OptionalStubConnector]:
    return [OptionalStubConnector(c["connector_id"], c["name"]) for c in OPTIONAL_CONNECTORS]
