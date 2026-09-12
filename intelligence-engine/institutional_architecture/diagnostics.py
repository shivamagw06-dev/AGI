"""RC-01 Architecture Center diagnostics."""

from __future__ import annotations

from typing import Any

from institutional_architecture.architecture_report import architecture_center_board
from institutional_architecture.conformance import run_conformance
from institutional_architecture.flags import flags_dict
from institutional_architecture.schema import (
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    AGIB_RELEASE_CANDIDATE,
    AGIB_RELEASE_STATUS,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    ARCH_ENGINE_VERSION,
    RC_PRODUCT,
    RC_VERSION,
    RC_WORKSTREAM_ID,
)


def build_diagnostics() -> dict[str, Any]:
    conf = run_conformance()
    board = architecture_center_board(conf)
    return {
        "workstream_id": RC_WORKSTREAM_ID,
        "product": RC_PRODUCT,
        "version": RC_VERSION,
        "arch_engine_version": ARCH_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_release_candidate": AGIB_RELEASE_CANDIDATE,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "agib_release_status": AGIB_RELEASE_STATUS,
        "flags": flags_dict(),
        **board,
        "conformance_ok": conf.get("ok"),
    }
