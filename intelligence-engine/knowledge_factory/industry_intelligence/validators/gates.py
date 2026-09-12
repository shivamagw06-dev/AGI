"""Quality gates — one FAIL ⇒ industry not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.industry_intelligence.schema import QUALITY_GATES, UNKNOWN


def _present(modules: dict[str, Any], name: str) -> bool:
    mod = modules.get(name)
    if not isinstance(mod, dict):
        return False
    data = mod.get("data")
    if data is None:
        return False
    if data == UNKNOWN:
        return False
    if isinstance(data, dict) and not data:
        return False
    if isinstance(data, list) and not data:
        return False
    return True


def _has_provenance(modules: dict[str, Any]) -> bool:
    for mod in modules.values():
        if isinstance(mod, dict) and mod.get("provenance"):
            return True
    return False


def validate_industry(obj: dict[str, Any]) -> dict[str, Any]:
    modules = obj.get("modules") or {}
    gates: dict[str, dict[str, Any]] = {}
    for name in ("business_model", "value_chain", "accounting", "kpis", "valuation", "macro", "government"):
        ok = _present(modules, name)
        gates[name] = {"pass": ok, "reason": None if ok else f"{name}_missing"}
    prov_ok = _has_provenance(modules)
    gates["provenance"] = {"pass": prov_ok, "reason": None if prov_ok else "no_provenance"}
    gates["validation"] = {
        "pass": not bool(obj.get("validation_failed")),
        "reason": None if not obj.get("validation_failed") else "validation_failed",
    }
    failed = [g for g in QUALITY_GATES if not gates.get(g, {}).get("pass")]
    return {
        "industry_id": obj.get("industry_id"),
        "gates": gates,
        "failed_gates": failed,
        "gate_pass": len(failed) == 0,
        "institutional_ready": len(failed) == 0,
        "fabricated": False,
    }
