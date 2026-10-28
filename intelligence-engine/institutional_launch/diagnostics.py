"""L-01 Launch Center diagnostics soft-slice."""

from __future__ import annotations

from typing import Any

from institutional_launch.flags import flags_dict
from institutional_launch.launch_report import launch_center_board
from institutional_launch.schema import (
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    LAUNCH_ENGINE_VERSION,
    L_PRODUCT,
    L_VERSION,
    L_WORKSTREAM_ID,
)


def build_diagnostics() -> dict[str, Any]:
    board = launch_center_board()
    return {
        "workstream_id": L_WORKSTREAM_ID,
        "product": L_PRODUCT,
        "version": L_VERSION,
        "launch_engine_version": LAUNCH_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "flags": flags_dict(),
        **board,
    }
