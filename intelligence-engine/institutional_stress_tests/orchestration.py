"""Orchestration gate — no individual module can pass IST alone."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from institutional_stress_tests.schema import (
    OPTIONAL_MODULES,
    ORCHESTRATION_PASS_RATIO,
    REQUIRED_MODULES,
)


def contributing_modules(probes: Mapping[str, Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for mod, row in (probes or {}).items():
        if not isinstance(row, Mapping):
            continue
        if row.get("contributing") is True:
            out.append(str(mod))
    return sorted(set(out))


def evaluate_orchestration(
    probes: Mapping[str, Mapping[str, Any]],
    *,
    required: Sequence[str] | None = None,
    optional: Sequence[str] | None = None,
) -> dict[str, Any]:
    """
    Hard gate: every required module must contribute.

    Automatic failures:
    - SINGLE_MODULE_RESPONSE — only one module contributed
    - MISSING_REQUIRED_MODULES — any required module missing
    - ORCHESTRATION_INCOMPLETE — contribution ratio below threshold
    """
    req = list(required or REQUIRED_MODULES)
    opt = list(optional or OPTIONAL_MODULES)
    hit = contributing_modules(probes)
    hit_set = set(hit)
    missing = [m for m in req if m not in hit_set]
    optional_hit = [m for m in opt if m in hit_set]
    ratio = (len(req) - len(missing)) / max(1, len(req))

    failures: list[str] = []
    if len(hit) <= 1:
        failures.append("SINGLE_MODULE_RESPONSE")
    if missing:
        failures.append("MISSING_REQUIRED_MODULES")
    if ratio < float(ORCHESTRATION_PASS_RATIO):
        failures.append("ORCHESTRATION_INCOMPLETE")

    return {
        "ok": not failures,
        "required": req,
        "required_hit": [m for m in req if m in hit_set],
        "missing_required": missing,
        "optional_hit": optional_hit,
        "contributing": hit,
        "contribution_ratio": round(ratio, 4),
        "single_module": len(hit) <= 1,
        "failures": failures,
        "pass_rule": "all_required_modules_must_contribute",
        "note": "No individual module can pass this stress test on its own.",
    }
