"""P5.5 Decision Replay — reconstruct institutional context for auditability."""

from __future__ import annotations

from typing import Any

from investment_operations.util import now_iso, resolve_ticker, soft_call


def build_decision_replay(
    ticker: str,
    *,
    version: int | None = None,
    company_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Reconstruct the intelligence stack that would feed CID / Decision Engine.

    Does not re-issue recommendations. Read-only reconstruction for audit / debugging.
    """
    entity = resolve_ticker(ticker)
    versions = soft_call("kde_versions", _list_versions, entity)
    ledger = soft_call("kde_ledger", _load_ledger, entity)

    memory_v = None
    if version is not None:
        memory_v = soft_call("kde_version", _load_version, entity, int(version))
    else:
        memory_v = soft_call("kde_current", _load_current, entity)
        if company_pack and isinstance(company_pack.get("memory"), dict):
            memory_v = {**company_pack["memory"], "_ok": True}

    oie = None
    if company_pack and isinstance(company_pack.get("opportunity"), dict):
        oie = company_pack["opportunity"]
    else:
        oie = soft_call("opportunity", _oie, entity)

    graph = None
    if company_pack and isinstance(company_pack.get("knowledge_graph"), dict):
        graph = company_pack["knowledge_graph"]
    else:
        graph = soft_call("graph", _graph, entity, memory_v if memory_v.get("_ok") else None)

    scenarios = soft_call("scenarios", _scenarios, entity)
    hypotheses = soft_call("hypotheses", _hypotheses, entity)

    cid = soft_call("cid", _cid_snapshot, entity)
    de = soft_call("decision_engine_readonly", _de_readonly, entity)

    mem_ok = bool(memory_v.get("_ok") and (memory_v.get("ok") or memory_v.get("memory_version") or memory_v.get("entity")))
    chain = [
        {
            "step": "company_memory",
            "version": memory_v.get("memory_version") if mem_ok else None,
            "checksum": ((memory_v.get("version_envelope") or {}).get("checksum") if mem_ok else None),
            "present": mem_ok,
        },
        {
            "step": "knowledge_delta",
            "status": ((memory_v.get("memory_delta") or {}).get("status") if mem_ok else None),
            "present": mem_ok and bool(memory_v.get("memory_delta")),
        },
        {
            "step": "knowledge_graph",
            "n_nodes": (graph or {}).get("n_nodes"),
            "n_edges": (graph or {}).get("n_edges"),
            "present": bool((graph or {}).get("n_nodes")),
        },
        {
            "step": "opportunity_pack",
            "score": (oie or {}).get("score"),
            "research_priority": (oie or {}).get("research_priority"),
            "present": bool((oie or {}).get("ok")),
        },
        {
            "step": "scenarios",
            "present": bool(scenarios.get("_ok")),
        },
        {
            "step": "hypotheses",
            "present": bool(hypotheses.get("_ok")),
        },
        {
            "step": "cid",
            "present": bool(cid.get("_ok") and (cid.get("ticker") or cid.get("enabled"))),
            "coverage_score": cid.get("coverage_score"),
        },
        {
            "step": "decision_engine",
            "present": bool(de.get("_ok")),
            "mode": "read_only_snapshot",
            "note": "Governance unchanged — replay reconstructs inputs, does not invent recommendations.",
        },
    ]

    return {
        "entity": entity,
        "as_of": now_iso(),
        "requested_version": version,
        "replay_chain": chain,
        "company_memory": _thin_memory(memory_v) if mem_ok else None,
        "knowledge_delta": (memory_v.get("memory_delta") if mem_ok else None),
        "versions_available": (versions.get("versions") if versions.get("_ok") else [])[:20],
        "ledger_events_n": len((ledger.get("events") or [])) if ledger.get("_ok") else None,
        "opportunity": {
            "score": (oie or {}).get("score"),
            "research_priority": (oie or {}).get("research_priority"),
            "why_now": (oie or {}).get("why_now"),
        }
        if (oie or {}).get("ok")
        else None,
        "knowledge_graph": {
            "n_nodes": (graph or {}).get("n_nodes"),
            "n_edges": (graph or {}).get("n_edges"),
            "peers": (graph or {}).get("peers"),
            "themes": (graph or {}).get("themes"),
        }
        if (graph or {}).get("n_nodes")
        else None,
        "cid": {
            "attached": bool(cid.get("ticker") or cid.get("enabled")),
            "coverage_score": cid.get("coverage_score"),
            "has_opportunity": bool((cid.get("opportunity_intelligence") or {}).get("ok")),
            "has_memory": bool(cid.get("company_memory") or cid.get("memory")),
        }
        if cid.get("_ok")
        else None,
        "decision_engine": de if de.get("_ok") else {"mode": "unavailable", "read_only": True},
        "reproducible": mem_ok and bool((oie or {}).get("ok")),
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "audit_policy": "reconstruct_compiled_inputs_only",
    }


def _thin_memory(mem: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity": mem.get("entity"),
        "memory_version": mem.get("memory_version"),
        "compiled_at": mem.get("compiled_at"),
        "coverage": mem.get("coverage"),
        "version_envelope": mem.get("version_envelope"),
        "checksum": (mem.get("version_envelope") or {}).get("checksum"),
    }


def _list_versions(entity: str) -> dict[str, Any]:
    from knowledge_delta_engine.production import versions

    return versions(entity)


def _load_ledger(entity: str) -> dict[str, Any]:
    from knowledge_delta_engine.production import ledger

    return ledger(entity)


def _load_version(entity: str, ver: int) -> dict[str, Any]:
    from knowledge_delta_engine.production import version

    row = version(entity, ver)
    return row.get("memory") or row


def _load_current(entity: str) -> dict[str, Any]:
    from knowledge_delta_engine.versioning import load_current

    return load_current(entity) or {"ok": False, "entity": entity}


def _oie(entity: str) -> dict[str, Any]:
    from opportunity_intelligence.production import analyse

    return analyse(entity, persist_memory=False)


def _graph(entity: str, memory: dict[str, Any] | None) -> dict[str, Any]:
    from investment_knowledge_graph.build import build_company_graph

    return build_company_graph(entity, memory=memory)


def _scenarios(entity: str) -> dict[str, Any]:
    from institutional_scenario_intelligence.production import company

    return company(entity)


def _hypotheses(entity: str) -> dict[str, Any]:
    from hypothesis_engine.production import health

    return health()


def _cid_snapshot(entity: str) -> dict[str, Any]:
    from cid.production import get_dossier

    return get_dossier(entity)


def _de_readonly(entity: str) -> dict[str, Any]:
    """Soft read-only presence check — never runs recommendation path as authority."""
    try:
        from decision_engine_v2.production import health

        h = health()
        return {
            "enabled": h.get("status") == "ok" or bool(h),
            "engine": "decision_engine_v2",
            "ticker": entity,
            "mode": "read_only",
            "issues_recommendations": False,
            "health": {"status": h.get("status"), "version": h.get("version")},
        }
    except Exception:
        try:
            from decision_engine.production import health

            h = health()
            return {
                "enabled": True,
                "engine": "decision_engine",
                "ticker": entity,
                "mode": "read_only",
                "health": h,
            }
        except Exception as exc:  # noqa: BLE001
            return {"enabled": False, "error": str(exc)[:120], "mode": "read_only"}
