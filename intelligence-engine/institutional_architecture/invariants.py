"""Declarative AGIB v1.0 architecture invariants (RC-01)."""

from __future__ import annotations

import importlib
from typing import Any, Callable, List, Tuple

Check = Callable[[], Tuple[bool, str]]


def _ok(msg: str) -> Tuple[bool, str]:
    return True, msg


def _fail(msg: str) -> Tuple[bool, str]:
    return False, msg


def check_kg_sole_graph_owner() -> Tuple[bool, str]:
    try:
        from institutional_graph.schema import KG_WORKSTREAM_ID
        from institutional_cross_company.schema import GRAPH_SYSTEM_OF_RECORD, GRAPH_PACKAGE

        if KG_WORKSTREAM_ID != "KG-01":
            return _fail("KG workstream id drift")
        if GRAPH_SYSTEM_OF_RECORD != "KG-01":
            return _fail("CCI does not declare KG-01 as graph SoR")
        if GRAPH_PACKAGE != "institutional_graph":
            return _fail("CCI graph package drift")
        return _ok("Knowledge Graph (KG-01) is the only graph owner; CCI reasons over it")
    except Exception as exc:
        return _fail(f"KG ownership check failed: {exc}")


def check_cci_owns_relationships_not_graph() -> Tuple[bool, str]:
    try:
        from institutional_cross_company.schema import CCI_ROLE, GRAPH_SYSTEM_OF_RECORD

        if "relationship" not in CCI_ROLE and "kg" not in CCI_ROLE:
            return _fail(f"CCI role unexpected: {CCI_ROLE}")
        if GRAPH_SYSTEM_OF_RECORD != "KG-01":
            return _fail("CCI claims graph ownership")
        return _ok("CCI owns relationships, not graph state")
    except Exception as exc:
        return _fail(f"CCI check failed: {exc}")


def check_uag_orchestration_not_recommendations() -> Tuple[bool, str]:
    try:
        from institutional_orchestrator.production import health
        from institutional_orchestrator.schema import UAG_ROLE

        h = health()
        if h.get("generates_recommendations") is not False:
            return _fail("UAG health claims recommendation generation")
        if "orchestration" not in UAG_ROLE:
            return _fail(f"UAG role not orchestration: {UAG_ROLE}")
        return _ok("UAG owns orchestration, not recommendations")
    except Exception as exc:
        return _fail(f"UAG check failed: {exc}")


def check_pub_compose_not_reasoning() -> Tuple[bool, str]:
    try:
        from institutional_publishing.production import health
        from institutional_publishing.schema import PUB_ROLE

        h = health()
        if h.get("compose_only") is not True:
            return _fail("PUB health not compose_only")
        if h.get("analyzes") is not False:
            return _fail("PUB health claims analysis")
        if h.get("generates_recommendations") is not False:
            return _fail("PUB generates recommendations")
        if "compose" not in PUB_ROLE and "no_analysis" not in PUB_ROLE:
            return _fail(f"PUB role unexpected: {PUB_ROLE}")
        return _ok("PUB owns composition, not reasoning")
    except Exception as exc:
        return _fail(f"PUB check failed: {exc}")


def check_mpc_tenancy_not_intelligence() -> Tuple[bool, str]:
    try:
        from institutional_multi_portfolio.production import health

        h = health()
        if h.get("owns_intelligence") is not False:
            return _fail("MPC owns intelligence")
        if h.get("intelligence_is_global") is not True:
            return _fail("MPC does not declare intelligence global")
        return _ok("MPC owns tenancy, not intelligence")
    except Exception as exc:
        return _fail(f"MPC check failed: {exc}")


def check_security_never_modifies_intelligence() -> Tuple[bool, str]:
    try:
        from institutional_security.production import health
        from institutional_security.schema import ADDS_INTELLIGENCE_ENGINES

        h = health()
        if h.get("enters_intelligence_layer") is not False:
            return _fail("Security enters intelligence layer")
        if ADDS_INTELLIGENCE_ENGINES is not False:
            return _fail("Security adds intelligence engines")
        return _ok("Security never modifies intelligence")
    except Exception as exc:
        return _fail(f"Security check failed: {exc}")


def check_observability_never_changes_execution() -> Tuple[bool, str]:
    try:
        from institutional_observability.production import health
        from institutional_observability.schema import ADDS_INTELLIGENCE_ENGINES

        h = health()
        if h.get("changes_platform_behavior") is not False:
            return _fail("Observability changes platform behavior")
        if ADDS_INTELLIGENCE_ENGINES is not False:
            return _fail("Observability adds intelligence engines")
        return _ok("Observability never changes execution")
    except Exception as exc:
        return _fail(f"Observability check failed: {exc}")


def check_performance_no_business_logic() -> Tuple[bool, str]:
    try:
        from institutional_performance.production import health
        from institutional_performance.schema import ADDS_INTELLIGENCE_ENGINES, ARCHITECTURE_FROZEN

        h = health()
        if ADDS_INTELLIGENCE_ENGINES is not False:
            return _fail("Performance adds intelligence engines")
        if ARCHITECTURE_FROZEN is not True:
            return _fail("Performance does not declare architecture frozen")
        if h.get("adds_intelligence_engines") is not False:
            return _fail("Performance health claims intelligence engines")
        return _ok("Performance layer never owns business logic")
    except Exception as exc:
        return _fail(f"Performance check failed: {exc}")


def check_architecture_freeze() -> Tuple[bool, str]:
    frozen = []
    for pkg in (
        "institutional_performance",
        "institutional_security",
        "institutional_observability",
    ):
        try:
            mod = importlib.import_module(f"{pkg}.schema")
            if getattr(mod, "ARCHITECTURE_FROZEN", False) is not True:
                return _fail(f"{pkg} ARCHITECTURE_FROZEN is not True")
            if getattr(mod, "ADDS_INTELLIGENCE_ENGINES", True) is not False:
                return _fail(f"{pkg} ADDS_INTELLIGENCE_ENGINES is not False")
            frozen.append(pkg)
        except Exception as exc:
            return _fail(f"Freeze check {pkg}: {exc}")
    return _ok(f"Architecture frozen across production packages: {', '.join(frozen)}")


def check_rw_presentation_only() -> Tuple[bool, str]:
    try:
        from institutional_workspace.production import health

        h = health()
        if h.get("mutates_system_intelligence") is not False:
            return _fail("RW mutates system intelligence")
        if h.get("generates_recommendations") is not False:
            return _fail("RW generates recommendations")
        return _ok("RW is presentation-only; notes never mutate system intelligence")
    except Exception as exc:
        return _fail(f"RW check failed: {exc}")


INTELLIGENCE_CHECKS: List[Tuple[str, Check]] = [
    ("kg_sole_graph_owner", check_kg_sole_graph_owner),
    ("cci_relationships_not_graph", check_cci_owns_relationships_not_graph),
    ("uag_orchestration_not_recommendations", check_uag_orchestration_not_recommendations),
    ("pub_compose_not_reasoning", check_pub_compose_not_reasoning),
    ("mpc_tenancy_not_intelligence", check_mpc_tenancy_not_intelligence),
    ("rw_presentation_only", check_rw_presentation_only),
]

PRODUCTION_CHECKS: List[Tuple[str, Check]] = [
    ("security_never_modifies_intelligence", check_security_never_modifies_intelligence),
    ("observability_never_changes_execution", check_observability_never_changes_execution),
    ("performance_no_business_logic", check_performance_no_business_logic),
    ("architecture_freeze", check_architecture_freeze),
]


def run_invariant_checks() -> dict[str, Any]:
    results = []
    for group, checks in (
        ("intelligence", INTELLIGENCE_CHECKS),
        ("production", PRODUCTION_CHECKS),
    ):
        for name, fn in checks:
            ok, msg = fn()
            results.append(
                {
                    "group": group,
                    "id": name,
                    "ok": ok,
                    "message": msg,
                    "severity": "pass" if ok else "violation",
                }
            )
    passed = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]
    return {
        "ok": not failed,
        "passed": passed,
        "failed": len(failed),
        "total": len(results),
        "results": results,
        "violations": failed,
    }
