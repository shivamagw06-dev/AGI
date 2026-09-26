"""IKL production façade — soft-wire only. Never raises to callers."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_layer.consult import consult, package_for_ask_agi
from institutional_knowledge_layer.flags import (
    ikl_ask_consult_enabled,
    ikl_delta_enabled,
    ikl_enabled,
    ikl_writeback_enabled,
)
from institutional_knowledge_layer.schema import (
    ASK_RETRIEVAL_ORDER,
    COMPANY_MEMORY_SLOTS,
    EXTRACTION_SLOTS,
    IKL_CODE,
    IKL_VERSION,
    MISSION,
    PROGRAMME,
    PROGRAMME_SHORT,
)
from institutional_knowledge_layer import store
from institutional_knowledge_layer.writeback import learn_from_cgl_run, learn_from_document


def health() -> dict[str, Any]:
    try:
        return {
            "status": "ok" if ikl_enabled() else "disabled",
            "engine": IKL_CODE,
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": IKL_VERSION,
            "mission": MISSION,
            "flags": {
                "IKL_ENABLED": ikl_enabled(),
                "IKL_WRITEBACK_ENABLED": ikl_writeback_enabled(),
                "IKL_ASK_CONSULT_ENABLED": ikl_ask_consult_enabled(),
                "IKL_DELTA_ENABLED": ikl_delta_enabled(),
            },
            "ask_retrieval_order": list(ASK_RETRIEVAL_ORDER),
            "extraction_slots": list(EXTRACTION_SLOTS),
            "company_memory_slots": list(COMPANY_MEMORY_SLOTS),
            "counts": {
                "companies": len(store.list_memory_keys("company", limit=500)),
                "industries": len(store.list_memory_keys("industry", limit=500)),
                "macro": len(store.list_memory_keys("macro", limit=500)),
            },
            "not_a_second_knowledge_system": True,
            "issues_recommendations": False,
            "pipeline": [
                "gather",
                "documents",
                "embeddings",
                "knowledge_extraction",
                "entity_memory",
                "knowledge_graph",
                "ask_agi",
            ],
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "engine": IKL_CODE, "error": str(exc)[:200]}


def on_document(doc: Any) -> dict[str, Any]:
    try:
        return learn_from_document(doc)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "soft": True}


def after_cgl_cycle(cgl_run: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return learn_from_cgl_run(cgl_run)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "soft": True}


def ask_consult(
    question: str,
    *,
    ticker: str | None = None,
    companies: list[str] | None = None,
    industries: list[str] | None = None,
) -> dict[str, Any]:
    try:
        return consult(
            question=question,
            ticker=ticker,
            companies=companies,
            industries=industries,
        )
    except Exception as exc:  # noqa: BLE001
        return {"enabled": False, "error": str(exc)[:200], "soft": True}


def memory_snapshot(ticker: str) -> dict[str, Any]:
    try:
        from institutional_knowledge_layer.memory.company import read_company_memory

        mem = read_company_memory(ticker)
        return {"ok": bool(mem), "ticker": (ticker or "").upper(), "memory": mem}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}


__all__ = [
    "health",
    "on_document",
    "after_cgl_cycle",
    "ask_consult",
    "package_for_ask_agi",
    "memory_snapshot",
]
