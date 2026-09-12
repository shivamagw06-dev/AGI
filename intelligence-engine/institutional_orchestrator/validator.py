"""UAG-01 quality gates — reject incomplete orchestration responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from institutional_orchestrator.models import InstitutionalQuery, InstitutionalResponse
from institutional_orchestrator.schema import VALIDATOR_VERSION


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    gates: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "gates": dict(self.gates),
            "validator_version": VALIDATOR_VERSION,
        }


def validate_response(
    query: InstitutionalQuery,
    response: InstitutionalResponse,
) -> ValidationResult:
    errors: list[str] = []
    gates: dict[str, bool] = {}

    has_plan = bool(query.execution_plan) and bool(response.execution_plan)
    gates["execution_plan_present"] = has_plan
    if not has_plan:
        errors.append("no execution plan")

    has_objects = bool(response.objects_consulted) or bool(response.supporting_evidence)
    gates["supporting_objects_present"] = has_objects
    if not has_objects:
        errors.append("no supporting objects")

    # Entity ambiguity: multiple tickers mentioned without resolution for company intents
    ambiguous = (
        query.intent == "Company Analysis"
        and len(query.entities) > 3
        and not response.objects_consulted
    )
    gates["entity_ambiguity_resolved"] = not ambiguous
    if ambiguous:
        errors.append("unresolved entity ambiguity")

    # Factual claims need evidence refs when we assert status/recommendation-like content
    factual = any(
        k in (response.direct_answer or "").lower()
        for k in ("recommendation", "status", "violation", "risk", "approved", "deferred")
    )
    has_evidence = bool(response.supporting_evidence) or bool(response.evidence_lineage)
    gates["evidence_for_claims"] = (not factual) or has_evidence
    if factual and not has_evidence:
        errors.append("missing evidence for factual claims")

    # Conflicting authoritative objects — e.g. committee Rejected vs decision Maintain without note
    gates["no_unexplained_conflict"] = True  # soft: builder surfaces both; hard reject rare
    conflict = _detect_conflict(response)
    if conflict:
        gates["no_unexplained_conflict"] = False
        errors.append("conflicting authoritative objects")

    gates["does_not_generate_recommendations"] = response.generates_recommendations is False
    if response.generates_recommendations:
        errors.append("orchestrator must not generate recommendations")

    has_diagnostics = bool(response.diagnostics)
    gates["diagnostics_present"] = has_diagnostics
    if not has_diagnostics:
        errors.append("missing diagnostics")

    return ValidationResult(ok=len(errors) == 0, errors=tuple(errors), gates=gates)


def _detect_conflict(response: InstitutionalResponse) -> bool:
    """Very narrow conflict detector — reject only when clearly contradictory without explanation."""
    text = (response.direct_answer or "").lower()
    # If we somehow claim both approved and rejected without conditions language
    if "rejected" in text and "approved" in text and "condition" not in text:
        return True
    return False
