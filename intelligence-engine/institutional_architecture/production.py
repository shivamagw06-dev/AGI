"""RC-01 production façades — conformance run / Architecture Center."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_architecture.architecture_report import architecture_center_board
from institutional_architecture.conformance import run_conformance
from institutional_architecture.diagnostics import build_diagnostics
from institutional_architecture.flags import fail_on_violation, flags_dict, is_enabled
from institutional_architecture.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_GA_SPEC,
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    AGIB_RELEASE_CANDIDATE,
    AGIB_RELEASE_STATUS,
    ARCHITECTURE_FROZEN,
    ARCH_ENGINE_VERSION,
    GUIDING_PRINCIPLE,
    RC_PRODUCT,
    RC_ROLE,
    RC_SPEC,
    RC_VERSION,
    RC_WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_CACHE: dict[str, Any] = {}
_CACHE_TTL = 30.0


def reset_for_tests() -> None:
    _CACHE.clear()


def _cached_conformance(*, force: bool = False) -> dict[str, Any]:
    now = time.time()
    if (
        not force
        and _CACHE.get("result")
        and now - float(_CACHE.get("ts") or 0) < _CACHE_TTL
    ):
        return dict(_CACHE["result"])
    result = run_conformance()
    _CACHE["result"] = result
    _CACHE["ts"] = now
    return result


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": RC_WORKSTREAM_ID,
        "product": RC_PRODUCT,
        "version": RC_VERSION,
        "role": RC_ROLE,
        "llm": False,
        "is_quality_gate": True,
        "is_feature": False,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_release_candidate": AGIB_RELEASE_CANDIDATE,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "agib_release_status": AGIB_RELEASE_STATUS,
        "ga_spec": AGIB_GA_SPEC,
        "arch_engine_version": ARCH_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "fail_on_violation": fail_on_violation(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": RC_SPEC,
        "brand": "AGI",
        "programme": "RC",
        "phase": "general_availability",
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    if not is_enabled():
        return {
            "status": "disabled",
            "workstream_id": RC_WORKSTREAM_ID,
            "architecture_center": True,
        }
    conf = _cached_conformance()
    board = architecture_center_board(conf)
    return {
        "status": "ok" if conf.get("ok") else "violations",
        "workstream_id": RC_WORKSTREAM_ID,
        "product": RC_PRODUCT,
        "version": RC_VERSION,
        "llm": False,
        **board,
    }


def run(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    force = bool(body.get("force") or body.get("refresh"))
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": RC_WORKSTREAM_ID}
    result = _cached_conformance(force=force)
    return {
        "ok": result["ok"],
        "workstream_id": RC_WORKSTREAM_ID,
        "product": RC_PRODUCT,
        "version": RC_VERSION,
        "architecture_score": result.get("architecture_score"),
        "violation_count": result.get("violation_count"),
        "violations": result.get("violations"),
        "sections": result.get("sections"),
        "import_graph": result.get("import_graph"),
        "layers": result.get("layers"),
        "report": result.get("report"),
        "agib_release_candidate": AGIB_RELEASE_CANDIDATE,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "agib_release_status": AGIB_RELEASE_STATUS,
        "release_candidate_ready": (result.get("architecture_score") or {}).get(
            "release_candidate_ready"
        ),
        "is_quality_gate": True,
        "is_feature": False,
        "as_of": now_iso(),
    }


def report_api() -> dict[str, Any]:
    result = _cached_conformance()
    return {
        "ok": result["ok"],
        "workstream_id": RC_WORKSTREAM_ID,
        "report": result.get("report"),
        "architecture_score": result.get("architecture_score"),
    }


def violations_api() -> dict[str, Any]:
    result = _cached_conformance()
    return {
        "ok": result["ok"],
        "workstream_id": RC_WORKSTREAM_ID,
        "violation_count": result.get("violation_count"),
        "violations": result.get("violations"),
    }


def diagnostics_api() -> dict[str, Any]:
    return {"ok": True, **build_diagnostics()}
