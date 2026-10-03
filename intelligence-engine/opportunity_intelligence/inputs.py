"""Soft-load compiled intelligence only — never query raw market APIs."""

from __future__ import annotations

from typing import Any

from opportunity_intelligence.util import resolve_ticker


def load_company_memory(
    ticker: str,
    *,
    injected_memory: dict[str, Any] | None = None,
    compile_if_missing: bool = True,
    persist: bool = False,
) -> dict[str, Any]:
    entity = resolve_ticker(ticker)
    if isinstance(injected_memory, dict) and injected_memory.get("ok"):
        return {**injected_memory, "entity": injected_memory.get("entity") or entity}

    # Prefer versioned current from Knowledge Delta Engine
    try:
        from knowledge_delta_engine.versioning import load_current

        mem = load_current(entity)
        if isinstance(mem, dict) and mem.get("ok"):
            return mem
    except Exception:
        pass

    if not compile_if_missing:
        return {"ok": False, "entity": entity, "error": "memory_missing"}

    # Incremental compile (owns versioning when persist=True)
    try:
        from knowledge_delta_engine.compile import incremental_compile

        mem = incremental_compile(entity, persist=persist)
        if isinstance(mem, dict) and mem.get("ok"):
            return mem
    except Exception as exc:  # noqa: BLE001
        err = str(exc)[:160]
    else:
        err = ((mem or {}).get("error") if isinstance(mem, dict) else None) or "compile_failed"

    try:
        from company_memory.production import compile as memory_compile

        mem = memory_compile(entity, persist=persist)
        if isinstance(mem, dict) and mem.get("ok"):
            return mem
        return {"ok": False, "entity": entity, "error": (mem or {}).get("error") or err}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "entity": entity, "error": str(exc)[:160]}


def load_knowledge_delta(memory: dict[str, Any]) -> dict[str, Any] | None:
    delta = memory.get("memory_delta") if isinstance(memory, dict) else None
    if isinstance(delta, dict):
        return delta
    return None


def load_knowledge_graph(
    ticker: str,
    *,
    memory: dict[str, Any] | None = None,
    injected_graph: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if isinstance(injected_graph, dict) and injected_graph.get("nodes"):
        return injected_graph
    try:
        from investment_knowledge_graph.build import build_company_graph

        g = build_company_graph(ticker, memory=memory)
        return g if isinstance(g, dict) and g.get("n_nodes") else None
    except Exception:
        return None


def load_scenarios(
    ticker: str,
    *,
    injected_scenarios: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if isinstance(injected_scenarios, dict):
        return injected_scenarios
    try:
        from institutional_scenario_intelligence.production import company as scenario_company

        pack = scenario_company(ticker)
        return pack if isinstance(pack, dict) else None
    except Exception:
        return None


def load_hypotheses(
    ticker: str,
    *,
    injected_hypotheses: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if isinstance(injected_hypotheses, dict):
        return injected_hypotheses
    # Soft-read only — hypothesis engine APIs vary; never fail OIE
    for attr in ("analyse", "company", "for_ticker", "package_for_ask_agi"):
        try:
            mod = __import__("hypothesis_engine.production", fromlist=[attr])
            fn = getattr(mod, attr, None)
            if callable(fn):
                pack = fn(ticker)
                if isinstance(pack, dict):
                    return pack
        except Exception:
            continue
    try:
        from hypothesis_engine.production import health

        h = health()
        return {"enabled": True, "engine_ok": h.get("status") == "ok", "hypotheses": []}
    except Exception:
        return None


def load_confidence(
    ticker: str,
    *,
    injected_confidence: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if isinstance(injected_confidence, dict):
        return injected_confidence
    # Soft presence check only — full ICC calibrate requires IEW/IHG/IHE/ICR packs.
    try:
        from institutional_confidence_calibration.production import status as icc_status

        h = icc_status()
        return {
            "enabled": True,
            "engine_ok": h.get("status") in {"ok", "ready"},
            "ticker": resolve_ticker(ticker),
            "icc_version": h.get("version") or h.get("confidence_version"),
        }
    except Exception:
        return None


def gather_inputs(
    ticker: str,
    *,
    injected_memory: dict[str, Any] | None = None,
    injected_graph: dict[str, Any] | None = None,
    injected_scenarios: dict[str, Any] | None = None,
    injected_hypotheses: dict[str, Any] | None = None,
    injected_confidence: dict[str, Any] | None = None,
    compile_if_missing: bool = True,
    persist_memory: bool = False,
) -> dict[str, Any]:
    entity = resolve_ticker(ticker)
    memory = load_company_memory(
        entity,
        injected_memory=injected_memory,
        compile_if_missing=compile_if_missing,
        persist=persist_memory,
    )
    return {
        "entity": entity,
        "memory": memory,
        "memory_delta": load_knowledge_delta(memory),
        "knowledge_graph": load_knowledge_graph(entity, memory=memory, injected_graph=injected_graph),
        "scenarios": load_scenarios(entity, injected_scenarios=injected_scenarios),
        "hypotheses": load_hypotheses(entity, injected_hypotheses=injected_hypotheses),
        "confidence": load_confidence(entity, injected_confidence=injected_confidence),
    }
