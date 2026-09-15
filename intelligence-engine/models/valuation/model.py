"""Valuation Knowledge — advises VE on methodology selection; does not value."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, new_id, subject_id
from models.industry.model import IndustryEconomicsModel, resolve_industry
from models.objects import ValuationGuidance

SECTOR_RULES = {
    "banking": {
        "recommended": ["relative_pb", "residual_income"],
        "primary": "relative_pb",
        "avoid": ["relative_ev_sales", "ddm"],
        "rationale": ["Banks are balance-sheet businesses; P/B + ROE is the institutional default."],
    },
    "insurance": {
        "recommended": ["embedded_value", "relative_pe", "dcf_fcff"],
        "primary": "embedded_value",
        "avoid": ["relative_ev_sales"],
        "rationale": ["Life insurance is commonly framed via embedded value / VNB economics."],
    },
    "utilities": {
        "recommended": ["dcf_fcff", "relative_pb"],
        "primary": "dcf_fcff",
        "avoid": ["relative_peg"],
        "rationale": ["Long-duration regulated cash flows suit DCF."],
    },
    "power": {
        "recommended": ["dcf_fcff", "sotp", "relative_pb"],
        "primary": "dcf_fcff",
        "avoid": ["relative_peg"],
        "rationale": ["PPA/merchant mix and asset base favor DCF/SOTP."],
    },
    "it_services": {
        "recommended": ["dcf_fcff", "relative_pe", "relative_ev_ebitda"],
        "primary": "dcf_fcff",
        "avoid": ["relative_pb"],
        "rationale": ["Asset-light compounders — DCF and earnings multiples dominate."],
    },
    "software": {
        "recommended": ["relative_ev_sales", "dcf_fcff", "relative_pe"],
        "primary": "relative_ev_sales",
        "avoid": ["relative_pb"],
        "rationale": ["Growth software often valued on EV/Sales with path to profitability."],
    },
}


class ValuationKnowledgeModel(DomainModel):
    """Teach AGI when to use each valuation methodology. Advises VE; does not value."""

    domain = "valuation"
    version = "1.0.0"
    name = "Valuation Knowledge"

    def __init__(self) -> None:
        self.industry = IndustryEconomicsModel()

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        industry_id = resolve_industry(p)
        ind = self.industry.analyse(p)
        cfg_models = list((ind.outputs.get("industry") or {}).get("preferred_valuation_models") or [])
        rule = SECTOR_RULES.get(industry_id)
        if rule:
            recommended = list(rule["recommended"])
            primary = rule["primary"]
            avoid = list(rule["avoid"])
            rationale = list(rule["rationale"])
        else:
            recommended = cfg_models or ["dcf_fcff", "relative_pe", "relative_ev_ebitda"]
            primary = recommended[0]
            avoid = []
            rationale = ["Default institutional toolkit from industry configuration."]
        # Conglomerate override
        if bool(p.get("is_conglomerate")) or industry_id in {"infrastructure"} and bool(p.get("multi_segment")):
            if "sotp" not in recommended:
                recommended = ["sotp", *recommended]
            primary = "sotp"
            rationale.append("Multi-segment / conglomerate structure → SOTP preferred.")
        guidance = ValuationGuidance(
            subject_id=sid,
            industry_id=industry_id,
            recommended_models=recommended,
            primary_model=primary,
            rationale=rationale,
            avoid_models=avoid,
            version=self.version,
        )
        summary = f"For {sid} ({industry_id}), prefer {primary}. Recommended: {', '.join(recommended)}."
        return AnalysisResult(
            object_type="ValuationGuidance",
            object_id=new_id("vgl"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=1.0 if rule else 0.7,
            label=primary,
            confidence=0.8 if rule else 0.6,
            summary=summary,
            outputs={"valuation_guidance": guidance.to_dict()},
            explainability={"why": summary, "rationale": rationale, "advises": "VE", "performs_valuation": False},
        )
