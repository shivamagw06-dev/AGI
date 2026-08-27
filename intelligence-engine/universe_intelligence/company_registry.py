"""Company Registry — identity + coverage state above Knowledge Factory."""

from __future__ import annotations

from typing import Any

from universe_intelligence import store as iui_store
from universe_intelligence.coverage_levels import coverage_level_for
from universe_intelligence.coverage_score import coverage_score
from universe_intelligence.ici import institutional_coverage_index
from universe_intelligence.membership import memberships_for_company
from universe_intelligence.provenance import attach_object_provenance, field_with_provenance
from universe_intelligence.quality_gates import institutional_quality_gates
from universe_intelligence.schema import IUI_VERSION, envelope


def compile_company(ticker: str) -> dict[str, Any]:
    """Compile a company registry object with levels, ICI, gates, memberships."""
    e = ticker.upper()

    identity_block: dict[str, Any] = {}
    try:
        from knowledge_factory.institutional_depth import company_identity

        identity_block = company_identity(e)
    except Exception:
        identity_block = {"entity": e, "found": False}

    level = coverage_level_for(e)
    score = coverage_score(e)
    ici = institutional_coverage_index(e)
    gates = institutional_quality_gates(e)
    memberships = memberships_for_company(e)

    obj = attach_object_provenance(
        {
            "ticker": e,
            "identity": field_with_provenance(
                identity_block,
                source="knowledge_factory.institutional_depth",
                collector="company_registry",
                confidence=0.95 if identity_block.get("found") else 0.2,
                derived_from=["company_identity"],
            ),
            "coverage_level": level["coverage_level"],
            "coverage_level_name": level["coverage_level_name"],
            "institutional_coverage": bool(gates["institutional_ready"]),
            "coverage_score": score["coverage_score"],
            "coverage_components": score["components"],
            "ici": ici["ici"],
            "ici_band": ici["band"],
            "ici_components": ici["components"],
            "quality_gates": gates["gates"],
            "gates_passed": gates["passed"],
            "gates_total": gates["total"],
            "universe_memberships": memberships.get("memberships") or [],
            "iui_version": IUI_VERSION,
        },
        source="iui_company_registry",
        collector="company_registry.compile",
        confidence=0.95 if gates["institutional_ready"] else 0.7,
        derived_from=["coverage_levels", "ici", "quality_gates", "membership"],
    )
    iui_store.put_company(e, obj)
    return obj


def get_company(ticker: str, *, refresh: bool = False) -> dict[str, Any]:
    e = ticker.upper()
    if not refresh:
        cached = iui_store.get_company(e)
        if cached:
            return {"found": True, "company": cached, "fabricated": False}
    obj = compile_company(e)
    return {"found": True, "company": obj, "fabricated": False}


def register_universe_companies(universe_id: str = "NIFTY_500") -> dict[str, Any]:
    from universe_intelligence.registry import current_members

    members = current_members(universe_id)
    compiled = []
    for t in members:
        compiled.append(compile_company(t)["ticker"])
    return envelope(
        kind="company_registry_bootstrap",
        payload={
            "universe_id": universe_id.upper(),
            "n": len(compiled),
            "institutional_coverage_n": sum(
                1 for t in members if (iui_store.get_company(t) or {}).get("institutional_coverage")
            ),
        },
    )
