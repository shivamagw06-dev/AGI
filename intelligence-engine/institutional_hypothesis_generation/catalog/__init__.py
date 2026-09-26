"""Versioned IHG hypothesis catalogs."""

from __future__ import annotations

from typing import Any

from institutional_hypothesis_generation.catalog.v1_0_0 import CATALOG as _V1
from institutional_hypothesis_generation.schema import HYPOTHESIS_VERSION

_CATALOGS: dict[str, dict[str, Any]] = {
    _V1["catalog_id"]: _V1,
    "v1": _V1,
    "v1.0.0": _V1,
    "default": _V1,
}


def load_catalog(catalog_id: str | None = None) -> dict[str, Any]:
    key = str(catalog_id or HYPOTHESIS_VERSION or "default")
    if key in _CATALOGS:
        return dict(_CATALOGS[key])
    for c in _CATALOGS.values():
        if c.get("catalog_id") == key:
            return dict(c)
    return dict(_V1)


def active_catalog_id() -> str:
    return str(load_catalog().get("catalog_id") or HYPOTHESIS_VERSION)
