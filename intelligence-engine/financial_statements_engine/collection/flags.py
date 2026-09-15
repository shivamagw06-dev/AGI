"""FSE-02.1 feature flags — canonical ingest + temporary HD dual-write."""

from __future__ import annotations

import os


def _truthy(name: str, default: str = "true") -> bool:
    raw = os.environ.get(name, default)
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def canonical_ingest_enabled() -> bool:
    """When true, adapter collectors route evidence through FSE-02 ingest()."""
    return _truthy("FSE_02_CANONICAL_INGEST", "true")


def dual_write_hd_enabled() -> bool:
    """When true, collectors keep writing Historical Depth after FSE-02 ingest.

    Must remain enabled for this migration phase.
    """
    return _truthy("FSE_02_DUAL_WRITE_HD", "true")
