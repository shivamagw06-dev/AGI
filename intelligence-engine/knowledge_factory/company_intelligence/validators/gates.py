"""Quality gates — one FAIL ⇒ not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence.schema import (
    QUALITY_GATES,
    UNKNOWN,
    INSTITUTIONAL_COMPLETE_LEVEL,
)


IDENTITY_REQUIRED = ("company_name", "nse_symbol", "sector", "exchange")


def _field_value(mod: dict[str, Any], key: str) -> Any:
    fields = mod.get("fields") or {}
    cell = fields.get(key)
    if isinstance(cell, dict) and "value" in cell:
        return cell.get("value")
    return cell


def _module_present(obj: dict[str, Any], name: str) -> bool:
    mod = (obj.get("modules") or {}).get(name)
    return isinstance(mod, dict) and bool(mod)


def _has_provenance(mod: dict[str, Any]) -> bool:
    if not isinstance(mod, dict):
        return False
    if mod.get("provenance"):
        return True
    fields = mod.get("fields") or {}
    if not fields:
        # timeline may use events
        return bool(mod.get("events"))
    ok = 0
    for cell in fields.values():
        if isinstance(cell, dict) and cell.get("provenance"):
            ok += 1
    return ok > 0


def count_unknown_fields(obj: dict[str, Any]) -> int:
    n = 0
    for mod in (obj.get("modules") or {}).values():
        if not isinstance(mod, dict):
            continue
        for cell in (mod.get("fields") or {}).values():
            if isinstance(cell, dict):
                if cell.get("status") == "unknown" or cell.get("value") == UNKNOWN:
                    n += 1
            elif cell == UNKNOWN:
                n += 1
    return n


def validate_object(obj: dict[str, Any]) -> dict[str, Any]:
    gates: dict[str, dict[str, Any]] = {}
    modules = obj.get("modules") or {}

    # Identity incomplete?
    ident = modules.get("identity") or {}
    ident_ok = _module_present(obj, "identity")
    if ident_ok:
        for k in IDENTITY_REQUIRED:
            v = _field_value(ident, k)
            if v in (None, "", UNKNOWN):
                ident_ok = False
                break
    gates["identity"] = {"pass": ident_ok, "reason": None if ident_ok else "identity_incomplete"}

    for name in ("business_model", "products", "segments", "management", "ownership", "timeline"):
        present = _module_present(obj, name)
        gates[name] = {"pass": present, "reason": None if present else f"{name}_missing"}

    # Provenance on every present module
    prov_ok = True
    for name, mod in modules.items():
        if not _has_provenance(mod):
            prov_ok = False
            break
    gates["provenance"] = {"pass": prov_ok and bool(modules), "reason": None if prov_ok else "no_provenance"}

    # Validation flag from compile
    val_failed = bool(obj.get("validation_failed"))
    gates["validation"] = {"pass": not val_failed, "reason": None if not val_failed else "validation_failed"}

    failed = [g for g in QUALITY_GATES if not gates.get(g, {}).get("pass")]
    ready = len(failed) == 0 and int(obj.get("coverage_level") or 0) >= INSTITUTIONAL_COMPLETE_LEVEL
    # Institutional ready also requires Level 7 — but gate report itself is independent
    gate_pass = len(failed) == 0
    return {
        "gates": gates,
        "failed_gates": failed,
        "gate_pass": gate_pass,
        "institutional_ready": gate_pass and int(obj.get("coverage_level") or 0) >= INSTITUTIONAL_COMPLETE_LEVEL,
        "unknown_fields": count_unknown_fields(obj),
        "fabricated": False,
    }


def institutional_ready(obj: dict[str, Any]) -> bool:
    return bool(validate_object(obj).get("institutional_ready"))
