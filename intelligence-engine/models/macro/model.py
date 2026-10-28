"""Macro Model — industry/company sensitivity to macro factors (consumes EconomicModel)."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.economics.model import EconomicModel
from models.industry.model import IndustryEconomicsModel, resolve_industry


# Industry sensitivities to macro factors (config-like coefficients)
SENSITIVITY = {
    "it_services": {"repo_rate": -0.2, "usd_inr": 0.6, "gdp_growth": 0.3},
    "banking": {"repo_rate": 0.4, "credit_growth": 0.7, "gdp_growth": 0.5},
    "automobile": {"repo_rate": -0.6, "gdp_growth": 0.7, "crude_oil": -0.3},
    "cement": {"repo_rate": -0.5, "gdp_growth": 0.6, "infra_capex": 0.7},
    "steel": {"gdp_growth": 0.6, "commodity_stress": -0.5, "infra_capex": 0.5},
    "utilities": {"repo_rate": -0.3, "gdp_growth": 0.2, "inflation": -0.2},
    "default": {"repo_rate": -0.3, "gdp_growth": 0.4, "inflation": -0.2},
}


class MacroModel(DomainModel):
    """Map macro regime onto company/industry earnings sensitivity."""

    domain = "macro"
    version = "1.0.0"
    name = "Macro Transmission Model"

    def __init__(self) -> None:
        self.economics = EconomicModel()
        self.industry = IndustryEconomicsModel()

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        eco = self.economics.analyse(p)
        ind_id = resolve_industry(p)
        sens = SENSITIVITY.get(ind_id) or SENSITIVITY["default"]
        repo = num(p, "repo_rate", 0.065)
        gdp = num(p, "gdp_growth", 0.065)
        # Simple impact score: higher means more supportive for the subject
        impact = 0.5
        impact += sens.get("repo_rate", 0) * (0.065 - repo) * 5
        impact += sens.get("gdp_growth", 0) * (gdp - 0.05) * 5
        impact += sens.get("usd_inr", 0) * (num(p, "usd_inr_change", 0.0)) * 2
        impact = clamp(impact)
        label = "tailwind" if impact >= 0.6 else "neutral" if impact >= 0.4 else "headwind"
        summary = (
            f"{sid} ({ind_id}) faces macro {label}. "
            f"Regime={eco.label}; key sensitivities={list(sens.keys())}."
        )
        return AnalysisResult(
            object_type="MacroSensitivity",
            object_id=new_id("mac"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(impact, 4),
            label=label,
            confidence=0.64,
            summary=summary,
            outputs={
                "industry_id": ind_id,
                "sensitivities": sens,
                "economic_regime": eco.to_dict(),
                "impact": impact,
            },
            relationships=eco.relationships,
            explainability={"why": summary, "sensitivities": sens, "regime": eco.label},
        )
