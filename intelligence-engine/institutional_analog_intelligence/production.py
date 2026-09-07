"""Production façade for Institutional Memory & Analog Intelligence (IMAI)."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.dashboard.board import build_board
from institutional_analog_intelligence.registry.index import get_memory, list_memories
from institutional_analog_intelligence.retrieval.engine import retrieve_memories
from institutional_analog_intelligence.schema import FREEZE_LOCKS, IMAI_VERSION, MODULE_CODE
from institutional_analog_intelligence.store import list_records, record


def retrieve(
    *,
    question: str,
    evidence_graph: dict[str, Any] | None = None,
    playbook: dict[str, Any] | None = None,
    as_of: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    pack = retrieve_memories(
        question=question,
        evidence_graph=evidence_graph,
        playbook=playbook,
        as_of=as_of,
        top_k=top_k,
    )
    audit = record(pack)
    pack = dict(pack)
    pack["audit_record_id"] = audit.get("record_id")
    return pack


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "version": IMAI_VERSION,
        "status": "ready",
        "memory_count": len(list_memories()),
        "freeze_locks": dict(FREEZE_LOCKS),
        "distinct_from": "institutional_memory (ILM — learning/mistakes; untouched)",
        "objective": "Have we seen this before? — analogues, regimes, prior decisions, patterns",
    }


def board() -> dict[str, Any]:
    return build_board()


def audits(*, limit: int = 50) -> list[dict[str, Any]]:
    return list_records(limit=limit)


def memory(memory_id: str) -> dict[str, Any] | None:
    return get_memory(memory_id)


def catalog(*, limit: int = 100) -> list[dict[str, Any]]:
    rows = list_memories()
    return rows[: max(1, min(int(limit), 200))]
