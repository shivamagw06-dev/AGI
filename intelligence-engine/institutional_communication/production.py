"""ICE production facade."""

from __future__ import annotations

from typing import Any

from institutional_communication.adapter.institutional_answer import build_institutional_answer
from institutional_communication.dashboard.board import communication_dashboard
from institutional_communication.quality.gates import validate_communication
from institutional_communication.renderers.engine import render_communication
from institutional_communication.schema import FREEZE_LOCKS, ICE_VERSION, PROGRAMME
from institutional_communication import store


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "ice_version": ICE_VERSION,
        "soft_wire_only": True,
        "deterministic_renderer_only": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/institutional-communication",
        "fabricated": False,
    }


def communicate_from_ask(
    *,
    question: str,
    intent_resolution: dict[str, Any] | None = None,
    answer_assembly: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    playbook_selection: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    institutional_answer: dict[str, Any] | None = None,
    governance: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
    replay_id: str | None = None,
) -> dict[str, Any]:
    """Primary Ask soft-wire entry — consume B/C/IAP/IEG/IMAI objects only."""
    ia = build_institutional_answer(
        question=question,
        intent_resolution=intent_resolution,
        answer_assembly=answer_assembly,
        framework_selection=framework_selection,
        playbook_selection=playbook_selection,
        evidence_graph=evidence_graph,
        institutional_memory=institutional_memory,
        institutional_answer=institutional_answer,
        governance=governance,
        evidence=evidence,
        knowledge=knowledge,
        replay_id=replay_id,
    )
    return communicate(ia)


def communicate(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    rendered = render_communication(institutional_answer)
    validation = validate_communication(rendered, institutional_answer=institutional_answer)
    out = {
        **rendered,
        "institutional_answer": {
            "intent_v2": institutional_answer.get("intent_v2"),
            "as_of": institutional_answer.get("as_of"),
            "framework_ids": (institutional_answer.get("frameworks") or {}).get("framework_ids"),
            "evidence_count": len(((institutional_answer.get("evidence") or {}).get("items") or [])),
        },
        "validation": validation,
        "ok": bool(validation.get("passed")),
    }
    store.record(out)
    return out


def dashboard() -> dict[str, Any]:
    return communication_dashboard()


def history(*, limit: int = 50) -> dict[str, Any]:
    return {"n": min(limit, 500), "rows": store.list_rows(limit=limit), "fabricated": False}
