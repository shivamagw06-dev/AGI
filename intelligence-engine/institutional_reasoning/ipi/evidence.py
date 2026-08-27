"""Module 1 — Portfolio Evidence Intelligence.

Transforms research into a Portfolio Evidence Pack. Downstream consumers
never fetch raw research.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ipi.downside import compute_downside
from institutional_reasoning.ipi.exposure import compute_exposure
from institutional_reasoning.ipi.portfolio_book import default_book
from institutional_reasoning.ipi.risk import compute_risk
from institutional_reasoning.ipi.schema import IPI_VERSION

PACK_VERSION = "portfolio-evidence-pack-v1.0.0"


def _ie_fields(packs: dict[str, Any] | None) -> dict[str, Any]:
    packs = packs or {}
    ie = packs.get("institutional_evidence") or {}
    # Flatten nested institutional_evidence.pack if present
    nested = ie.get("institutional_evidence") if isinstance(ie.get("institutional_evidence"), dict) else {}
    out = dict(nested)
    out.update({k: v for k, v in ie.items() if k != "institutional_evidence"})
    validated = ie.get("validated") or nested.get("validated") or {}
    for k, v in validated.items():
        if isinstance(v, dict) and "value" in v and k not in out:
            out[k] = v.get("value")
    return out


def build_portfolio_evidence_pack(
    entity_id: str | None,
    *,
    entity_name: str | None = None,
    research_record: dict[str, Any] | None = None,
    existing_packs: dict[str, dict[str, Any]] | None = None,
    book: dict[str, Any] | None = None,
    proposed_weight: float | None = None,
    djg_reference: str | None = None,
) -> dict[str, Any]:
    if not entity_id:
        return {"found": False, "reason": "no_entity", "pack_version": PACK_VERSION}

    book = book or default_book()
    research_record = research_record or {}
    evidence = _ie_fields(existing_packs)
    # Also pull from research record institutional_evidence
    if not evidence.get("current_pe"):
        evidence.update(_ie_fields({"institutional_evidence": research_record.get("institutional_evidence") or {}}))

    risk = compute_risk(
        entity_id=entity_id,
        book=book,
        candidate_weight=proposed_weight,
    )
    downside = compute_downside(entity_id=entity_id, evidence=evidence, risk_inputs=risk)
    # Recompute risk with downside for tail
    risk = compute_risk(
        entity_id=entity_id,
        book=book,
        candidate_weight=proposed_weight,
        downside=downside,
    )
    exposure = compute_exposure(entity_id=entity_id, proposed_weight=proposed_weight, book=book)

    frameworks = research_record.get("frameworks") or []
    executed = [f for f in frameworks if f.get("status") == "executed"]
    # Coverage reflects the evidence actually bound to the candidate, not only
    # how many frameworks the research question happened to run.
    core_fields = ("current_pe", "historical_pe", "peer_pe", "sector_pe", "roic")
    field_coverage = sum(1 for f in core_fields if evidence.get(f) is not None) / len(core_fields)
    framework_coverage = (len(executed) / len(frameworks)) if frameworks else 0.0
    coverage = round(max(field_coverage, framework_coverage), 4)
    research_conf = None
    committee = research_record.get("committee") or {}
    if committee.get("confidence") is not None:
        try:
            research_conf = float(committee.get("confidence"))
        except (TypeError, ValueError):
            research_conf = None
    if research_conf is None:
        research_conf = round(0.55 + 0.35 * coverage, 4)

    base_ret = ((downside.get("base_case") or {}).get("expected_return")) if downside.get("computable") else None
    djg = research_record.get("justification_graph") or {}
    djg_ref = djg_reference or djg.get("run_id") or research_record.get("run_id")

    pack = {
        "found": True,
        "pack_version": PACK_VERSION,
        "ipi_version": IPI_VERSION,
        "security": entity_name or entity_id,
        "symbol": str(entity_id).upper(),
        "entity_id": str(entity_id).upper(),
        "expected_return": base_ret,
        "expected_downside": downside.get("expected_loss") if downside.get("computable") else None,
        "conviction": None,  # filled after sizing
        "evidence_coverage": coverage,
        "research_confidence": research_conf,
        "portfolio_fit": exposure.get("portfolio_fit"),
        "risk_contribution": risk.get("risk_contribution"),
        "exposure_impact": (exposure.get("exposure") or {}).get("sector_weight_after"),
        "liquidity": round(1.0 - float(risk.get("liquidity_risk") or 0.0), 4),
        "djg_reference": djg_ref,
        # Contract aliases
        "exposure": exposure.get("exposure"),
        "weight": (exposure.get("exposure") or {}).get("weight"),
        "allocation": (exposure.get("exposure") or {}).get("allocation"),
        "downside_case": downside.get("downside_case") if downside.get("computable") else None,
        "bear_case": downside.get("bear_case") if downside.get("computable") else None,
        "bear": downside.get("bear") if downside.get("computable") else None,
        "risk_share": risk.get("risk_share"),
        "var_contribution": risk.get("var_contribution"),
        "risk_drivers": risk.get("risk_drivers"),
        "portfolio_fit_score": exposure.get("portfolio_fit"),
        # Nested modules
        "downside_intel": downside,
        "risk": risk,
        "exposure_intel": exposure,
        "evidence_fields": {
            "current_pe": evidence.get("current_pe"),
            "historical_pe": evidence.get("historical_pe"),
            "peer_pe": evidence.get("peer_pe") or evidence.get("peer_median_pe"),
            "sector_pe": evidence.get("sector_pe"),
            "roic": evidence.get("roic"),
        },
        "computable": bool(downside.get("computable")),
        "withhold": bool(downside.get("withhold")),
    }
    return pack
