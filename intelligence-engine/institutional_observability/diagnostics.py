"""PRP-03 Operations Center diagnostics soft-slice."""

from __future__ import annotations

from typing import Any

from institutional_observability.dashboards import operations_center_board
from institutional_observability.flags import flags_dict
from institutional_observability.schema import (
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    OBS_ENGINE_VERSION,
    PRP_PRODUCT,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
)


def build_diagnostics() -> dict[str, Any]:
    board = operations_center_board()
    return {
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "obs_engine_version": OBS_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "flags": flags_dict(),
        **board,
    }
