"""Feature flags — IEP soft-gated; v1.1 foundation defaults ON for validation path."""

from __future__ import annotations

import os
from typing import Any, Dict


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_iep_enabled() -> bool:
    return _env_bool("AGI_IEP_ENABLED", True)


def iep_flags() -> Dict[str, Any]:
    return {
        "iep_enabled": is_iep_enabled(),
        "block_research_without_evidence": _env_bool("AGI_IEP_BLOCK_RESEARCH", True),
        "block_recommendation_without_statements": _env_bool(
            "AGI_IEP_BLOCK_RECOMMENDATION", True
        ),
        "block_publish_unless_ready": _env_bool("AGI_IEP_BLOCK_PUBLISH", True),
        "auto_ingest_on_ask": _env_bool("AGI_IEP_AUTO_INGEST", True),
        "phase1_top20_only": _env_bool("AGI_IEP_PHASE1_ONLY", True),
    }
