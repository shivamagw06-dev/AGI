"""IPI production facade — soft-wire under institutional_reasoning."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ipi.decision import decide_portfolio
from institutional_reasoning.ipi.evidence import build_portfolio_evidence_pack
from institutional_reasoning.ipi.memory import snapshot as memory_snapshot
from institutional_reasoning.ipi.portfolio_suite import run_portfolio_suite
from institutional_reasoning.ipi.schema import IPI_VERSION, MODULE_CODE, PHASE5_TARGETS, PROGRAMME

__all__ = [
    "dashboard",
    "decide_portfolio",
    "package_for_governance",
    "quality_gates",
    "run_portfolio_suite",
]


def package_for_governance(
    entity_id: str | None,
    *,
    entity_name: str | None = None,
    existing_packs: dict[str, dict[str, Any]] | None = None,
    research_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact pack injecting portfolio contract fields before validation."""
    if not entity_id:
        return {"found": False, "reason": "no_entity"}
    pep = build_portfolio_evidence_pack(
        entity_id,
        entity_name=entity_name,
        research_record=research_record,
        existing_packs=existing_packs,
    )
    if not pep.get("found"):
        return pep
    # Flat contract aliases only. Do NOT nest risk/evidence dicts here:
    # evidence_validation matches aliases with substring (`"pe" in key`), so
    # keys like expected_shortfall / expected_return would false-satisfy PE.
    return {
        "found": True,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IPI_VERSION,
        "pack_version": pep.get("pack_version"),
        "entity_id": pep.get("entity_id"),
        "symbol": pep.get("symbol"),
        # Scalar / safe structures only (validation deep-walks nested dicts).
        "weight": pep.get("weight"),
        "allocation": pep.get("allocation"),
        "exposure": pep.get("weight"),  # scalar alias — avoid nested exposure dict keys
        "risk_contribution": pep.get("risk_contribution"),
        "risk_share": pep.get("risk_share"),
        "var_contribution": pep.get("var_contribution"),
        # Scalars for downside aliases (dicts containing expected_return false-match "pe")
        "downside_case": (pep.get("downside_intel") or {}).get("downside")
        if pep.get("computable")
        else None,
        "bear": (pep.get("downside_intel") or {}).get("bear") if pep.get("computable") else None,
        "stress_case": (pep.get("downside_intel") or {}).get("stress_case")
        if pep.get("computable")
        else None,
        # expected_cagr/irr — NOT expected_return (substring-matches alias "pe").
        "expected_cagr": pep.get("expected_return"),
        "irr": pep.get("expected_return"),
        # Join list → string so evidence_validation walk binds the field
        # (bare string lists are not emitted as parent keys by the walker).
        "risk_drivers": ",".join((pep.get("risk") or {}).get("risk_drivers") or [])
        or None,
        "portfolio_fit": pep.get("portfolio_fit"),
        "liquidity": pep.get("liquidity"),
        "computable": pep.get("computable"),
        "withhold": pep.get("withhold"),
    }


def dashboard() -> dict[str, Any]:
    sample = decide_portfolio(entity_id="INFY", entity_name="Infosys", persist_memory=False)
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IPI_VERSION,
        "phase5_targets": PHASE5_TARGETS,
        "sample": {
            "entity_id": sample.get("entity_id"),
            "action": (sample.get("committee") or {}).get("action"),
            "target_weight": (sample.get("sizing") or {}).get("target_weight"),
            "withheld": sample.get("withheld"),
            "pdg_valid": ((sample.get("portfolio_decision_graph") or {}).get("integrity") or {}).get("valid"),
        },
        "portfolio_memory": memory_snapshot(),
    }


def quality_gates() -> dict[str, Any]:
    suite = run_portfolio_suite()
    return {
        "gate": "INSTITUTIONAL_PORTFOLIO_INTELLIGENCE",
        "version": IPI_VERSION,
        "portfolio_suite_score": suite.get("score"),
        "pdg_coverage_pct": suite.get("pdg_coverage_pct"),
        "unsupported_recommendations": suite.get("unsupported_recommendations"),
        "phase5_gate": suite.get("phase5_gate"),
        "passed": bool((suite.get("phase5_gate") or {}).get("passed")),
        "failures": [r for r in (suite.get("results") or []) if not r.get("passed")],
    }
