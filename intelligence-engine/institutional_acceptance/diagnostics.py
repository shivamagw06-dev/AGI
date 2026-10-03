"""PAT-01 diagnostics."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.flags import flags_dict, harness_mode, is_enabled
from institutional_acceptance.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    PAT_SPEC,
    PAT_VERSION,
    PAT_WORKSTREAM_ID,
    PHASES,
    SUCCESS_CRITERIA,
)


def build_diagnostics() -> dict[str, Any]:
    return {
        "workstream_id": PAT_WORKSTREAM_ID,
        "version": PAT_VERSION,
        "enabled": is_enabled(),
        "harness": harness_mode(),
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "guiding_principle": GUIDING_PRINCIPLE,
        "phases": [{"code": c, "key": k, "title": t} for c, k, t in PHASES],
        "success_criteria": dict(SUCCESS_CRITERIA),
        "flags": flags_dict(),
        "spec": PAT_SPEC,
    }
