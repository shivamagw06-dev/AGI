"""Institutional Knowledge Runtime v1.0 — public API."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.confidence import calculate_confidence
from institutional_knowledge_runtime.dependencies import resolve_dependencies
from institutional_knowledge_runtime.pipeline import list_unknowns, run_pipeline  # noqa: F401 — re-export
from institutional_knowledge_runtime.schema import IKR_OBJECT_REGISTRY, IKR_VERSION, PROGRAMME
from institutional_knowledge_runtime.selection import select_assertions
from institutional_knowledge_runtime.store import get, load_or_create_company, put
from institutional_knowledge_runtime.validation import validate_assertions
from institutional_knowledge_runtime.versioning import update_assertion, version_assertion
from institutional_knowledge_runtime.monitoring import list_monitoring


def load_object(
    entity_type: str,
    entity_id: str,
    *,
    company: str | None = None,
    iko: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    monitoring_metrics: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Load IKO and run full pipeline."""
    registry = IKR_OBJECT_REGISTRY.get(entity_type)
    if not registry or not registry.get("implemented"):
        return {
            "enabled": False,
            "error": f"Object type not implemented: {entity_type}",
            "entity_type": entity_type,
            "entity_id": entity_id,
        }

    if entity_type == "company":
        obj = load_or_create_company(entity_id, company=company, iko=iko)
    else:
        existing = get(entity_type, entity_id)
        if not existing:
            return {"enabled": False, "error": "object_not_found", "entity_type": entity_type, "entity_id": entity_id}
        obj = existing

    pack = run_pipeline(obj, evidence_graph=evidence_graph, monitoring_metrics=monitoring_metrics)
    pack["iko"] = obj
    return pack


def apply_ikr_runtime(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Soft-wire IKR into answer construction after Research Workflow Framework."""
    if not isinstance(out, dict):
        return out

    ticker = kwargs.get("ticker") or out.get("ticker")
    company = kwargs.get("company") or out.get("company")
    entity_id = str(ticker or company or "").strip()
    if not entity_id:
        out["institutional_knowledge_runtime"] = {
            "enabled": False,
            "bypassed": True,
            "reason": "no_entity_id",
        }
        return out

    evidence_graph = kwargs.get("evidence_graph") or out.get("evidence_graph")
    monitoring_metrics = kwargs.get("monitoring_metrics") or out.get("monitoring_metrics")
    iko = kwargs.get("iko") or out.get("iko")

    pack = load_object(
        "company",
        entity_id,
        company=company,
        iko=iko if isinstance(iko, dict) else None,
        evidence_graph=evidence_graph if isinstance(evidence_graph, dict) else None,
        monitoring_metrics=monitoring_metrics if isinstance(monitoring_metrics, dict) else None,
    )

    # Select assertions relevant to current research objective
    rwf = out.get("research_workflow_framework") if isinstance(out.get("research_workflow_framework"), dict) else {}
    objective = out.get("decision_objective") or (rwf.get("decision_objective") or {}).get("objective")
    categories = None
    if objective and "Valuation" in str(objective):
        categories = ["valuation_context", "investment_thesis"]
    elif objective and "Risk" in str(objective):
        categories = ["risks", "monitoring"]

    selection = select_assertions(pack, categories=categories, include_unknowns=True, limit=12)

    result = {
        "enabled": pack.get("enabled", True),
        "version": IKR_VERSION,
        "programme": PROGRAMME,
        "entity_id": entity_id.upper(),
        "entity_type": "company",
        "pipeline_steps": pack.get("pipeline_steps"),
        "steps_completed": pack.get("steps_completed"),
        "assertion_count": len(pack.get("assertions") or []),
        "unknown_count": len(pack.get("unknowns") or []),
        "contradiction_count": len(pack.get("contradictions") or []),
        "validation": pack.get("validation"),
        "selection": selection,
        "deterministic": True,
        "llm": False,
    }

    out["institutional_knowledge_runtime"] = result
    out["ikr_pack"] = pack
    out["ikr_selection"] = selection
    out["institutional_assertions"] = selection.get("assertions")
    out["institutional_unknowns"] = pack.get("unknowns")

    return out


def health() -> dict[str, Any]:
    implemented = sum(1 for v in IKR_OBJECT_REGISTRY.values() if v.get("implemented"))
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": IKR_VERSION,
        "object_types_registered": len(IKR_OBJECT_REGISTRY),
        "object_types_implemented": implemented,
        "deterministic": True,
        "llm": False,
        "writers_llm_allowed": False,
    }


__all__ = [
    "apply_ikr_runtime",
    "calculate_confidence",
    "health",
    "list_monitoring",
    "list_unknowns",
    "load_object",
    "resolve_dependencies",
    "select_assertions",
    "update_assertion",
    "validate_assertions",
    "version_assertion",
    "run_pipeline",
]
