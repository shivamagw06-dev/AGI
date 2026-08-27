"""Connector factory / plugin registry — add connectors without core changes."""

from __future__ import annotations

from typing import Any

from app.aoi.connector import SourceConnector
from app.aoi.connectors.company_ir import CompanyIrConnector
from app.aoi.connectors.exchanges import BseConnector, NseConnector
from app.aoi.connectors.global_macro import FredConnector, ImfConnector, WorldBankConnector
from app.aoi.connectors.macro_gov import MofConnector, MospiConnector, PibConnector, RbiConnector, SebiConnector
from app.aoi.connectors.optional import build_optional_stubs
from app.aoi.flags import AoiFlags
from app.aoi.sources_config import CONNECTOR_CONFIGS


_BUILDERS: dict[str, type[SourceConnector]] = {
    "company_ir": CompanyIrConnector,
    "nse": NseConnector,
    "bse": BseConnector,
    "rbi": RbiConnector,
    "sebi": SebiConnector,
    "mof": MofConnector,
    "mospi": MospiConnector,
    "fred": FredConnector,
    "imf": ImfConnector,
    "worldbank": WorldBankConnector,
    "pib": PibConnector,
}


def build_connectors(flags: AoiFlags, *, configs: dict[str, dict[str, Any]] | None = None) -> dict[str, SourceConnector]:
    cfgs = configs or CONNECTOR_CONFIGS
    out: dict[str, SourceConnector] = {}
    for cid, cls in _BUILDERS.items():
        if not flags.connector_enabled(cid):
            continue
        out[cid] = cls(config=dict(cfgs.get(cid) or {}), live_fetch=flags.aoi_live_fetch)
    return out


def list_optional_connectors() -> list[dict[str, str]]:
    return [
        {"connector_id": c.connector_id, "name": c.name, "status": "designed_not_implemented"}
        for c in build_optional_stubs()
    ]


def register_connector(connector_id: str, cls: type[SourceConnector]) -> None:
    """Runtime extension point — zero changes to pipeline required."""
    _BUILDERS[connector_id] = cls
