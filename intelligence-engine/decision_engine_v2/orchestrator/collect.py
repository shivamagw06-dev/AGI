"""Collect soft slices from every intelligence layer — soft read only, no redesign.

Never calls institutional_stack.company_pack (would recurse when stack soft-wires IDE V2).
"""

from __future__ import annotations

from typing import Any

from decision_engine_v2.schema import INPUT_LAYERS, PRIMARY_QUESTION


def _safe_slice(mod_path: str, ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    try:
        import importlib

        mod = importlib.import_module(mod_path)
        out = mod.soft_slice_for_analyst(ticker, analyst=analyst) or {}
        return out if isinstance(out, dict) else {}
    except Exception as exc:
        return {"_soft_error": str(exc)[:160]}


def _safe_irs(mod_path: str) -> dict[str, Any]:
    try:
        import importlib

        mod = importlib.import_module(mod_path)
        out = mod.soft_slice_for_irs() or {}
        return out if isinstance(out, dict) else {}
    except Exception as exc:
        return {"_soft_error": str(exc)[:160]}


def _unwrap(out: dict[str, Any], key: str) -> dict[str, Any]:
    if key in out and isinstance(out[key], dict):
        return out[key]
    if out and "_soft_error" not in out:
        return out
    return {"enabled": False, "error": out.get("_soft_error")}


def collect_inputs(ticker: str, *, question: str | None = None) -> dict[str, Any]:
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND"}
    t = aliases.get(t, t)
    layers: dict[str, Any] = {}

    fillers = {
        "filing_intelligence": "filing_intelligence.production",
        "filing_diff": "filing_diff.production",
        "management_intelligence": "management_intelligence.production",
        "accounting_intelligence": "accounting_intelligence.production",
        "peer_intelligence": "peer_intelligence.production",
        "causal_intelligence": "causal_graph.production",
        "knowledge_graph": "knowledge_graph.production",
        "forecast_intelligence": "forecast_intelligence.production",
        "institutional_memory": "institutional_memory.production",
        "simulation_lab": "simulation_lab.production",
        "portfolio_intelligence": "portfolio_intelligence.production",
    }
    for key, mod in fillers.items():
        layers[key] = _unwrap(_safe_slice(mod, t), key)

    eil = _safe_irs("academy.evidence.production")
    layers["evidence_intelligence"] = eil.get("evidence_intelligence") or eil

    layers["institutional_analysts"] = {
        "enabled": True,
        "present": True,
        "rule": "Specialist opinions soft-referenced; IDE V2 does not replace analysts",
    }
    layers["investment_committee"] = {
        "enabled": True,
        "present": True,
        "rule": "Committee soft-referenced; IDE V2 does not replace IC",
    }

    # Compact summary from soft slices (mirrors stack summary fields without calling stack)
    mii = layers.get("management_intelligence") or {}
    aci = layers.get("accounting_intelligence") or {}
    pio = layers.get("portfolio_intelligence") or {}
    cig = layers.get("causal_intelligence") or {}
    fie = layers.get("forecast_intelligence") or {}
    ilm = layers.get("institutional_memory") or {}
    ssl = layers.get("simulation_lab") or {}
    impact = pio.get("impact") if isinstance(pio.get("impact"), dict) else {}
    stack_summary = {
        "management_confidence": mii.get("confidence"),
        "management_dna": mii.get("dna"),
        "accounting_confidence": aci.get("confidence"),
        "accounting_behaviour": aci.get("behaviour"),
        "accounting_quality_score": aci.get("accounting_quality_score"),
        "manipulation_risk": aci.get("manipulation_risk"),
        "portfolio_id": pio.get("portfolio_id"),
        "portfolio_grade": pio.get("health_grade"),
        "portfolio_quality": pio.get("portfolio_quality"),
        "portfolio_net_effect": impact.get("net_portfolio_effect"),
        "portfolio_fit": (pio.get("suitability") or {}).get("portfolio_fit")
        if isinstance(pio.get("suitability"), dict)
        else None,
        "causal_confidence": cig.get("confidence"),
        "causal_why": (cig.get("why") or [None])[0] if isinstance(cig.get("why"), list) else cig.get("why"),
        "forecast_most_likely": fie.get("most_likely"),
        "forecast_confidence": fie.get("confidence"),
        "memory_lesson_count": ilm.get("lesson_count"),
        "memory_mistake_count": ilm.get("mistake_count"),
        "memory_thinking_improved": ilm.get("thinking_improved"),
        "simulation_scenario_id": ssl.get("scenario_id"),
        "simulation_expected_return": ssl.get("expected_return"),
        "simulation_confidence": ssl.get("confidence"),
    }

    present = {
        k: bool(layers.get(k)) and (layers.get(k) or {}).get("enabled", True) is not False
        for k in INPUT_LAYERS
    }
    return {
        "ticker": t,
        "question": question or PRIMARY_QUESTION,
        "layers": layers,
        "stack_summary": stack_summary,
        "inputs_present": present,
        "coverage": round(sum(1 for v in present.values() if v) / max(1, len(present)), 3),
        "soft_read_only": True,
        "not_an_engine_redesign": True,
        "avoids_stack_recursion": True,
    }
