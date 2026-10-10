"""FIML model registry — discover, version, analyse across domains."""

from __future__ import annotations

from typing import Any

from models.accounting import AccountingModel
from models.base import DomainModel
from models.business import BusinessModel
from models.capital_allocation import CapitalAllocationModel
from models.competition import CompetitionModel
from models.decision import DecisionModel
from models.economics import EconomicModel
from models.forecasting import ForecastingKnowledgeModel
from models.governance import GovernanceModel
from models.industry import IndustryEconomicsModel
from models.industry.model import list_industries
from models.macro import MacroModel
from models.risk import RiskModel
from models.valuation import ValuationKnowledgeModel

_REGISTRY: "ModelRegistry | None" = None


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, DomainModel] = {
            "accounting": AccountingModel(),
            "business": BusinessModel(),
            "industry": IndustryEconomicsModel(),
            "competition": CompetitionModel(),
            "capital_allocation": CapitalAllocationModel(),
            "economics": EconomicModel(),
            "macro": MacroModel(),
            "risk": RiskModel(),
            "governance": GovernanceModel(),
            "valuation": ValuationKnowledgeModel(),
            "forecasting": ForecastingKnowledgeModel(),
            "decision": DecisionModel(),
        }

    def list_models(self) -> list[dict[str, Any]]:
        return [m.meta().to_dict() for m in self._models.values()]

    def get(self, domain: str) -> DomainModel:
        key = (domain or "").lower().strip()
        if key not in self._models:
            raise KeyError(f"Unknown FIML domain: {domain}")
        return self._models[key]

    def analyse(self, domain: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).analyse(payload, **kwargs).to_dict()

    def score(self, domain: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).score(payload, **kwargs)

    def explain(self, domain: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).explain(payload, **kwargs)

    def compare(self, domain: str, left: dict[str, Any], right: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).compare(left, right, **kwargs)

    def monitor(self, domain: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).monitor(payload, **kwargs)

    def timeline(self, domain: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).timeline(payload, **kwargs)

    def relationships(self, domain: str, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self.get(domain).relationships(payload, **kwargs)

    def search(self, query: str, *, domain: str | None = None, limit: int = 20) -> dict[str, Any]:
        if domain:
            return self.get(domain).search(query, limit=limit)
        # Cross-model: industries + model metas
        ind = self.get("industry").search(query, limit=limit)
        metas = [m for m in self.list_models() if query.lower() in json_blob(m)]
        return {
            "query": query,
            "models": metas[:limit],
            "industries": ind.get("hits") or [],
            "industry_coverage": list_industries(),
        }

    def dependency_graph(self) -> dict[str, Any]:
        return {
            "library": "FIML",
            "version": "1.0.0",
            "consumers": {
                "EVE": ["accounting"],
                "KF": ["industry", "business"],
                "IIE": ["business", "competition", "capital_allocation", "governance", "industry"],
                "FLE": ["forecasting", "economics", "industry"],
                "MEE": ["economics", "macro", "risk"],
                "VE": ["valuation", "accounting", "industry"],
                "CAE": ["decision", "industry", "risk"],
                "IRP": ["decision", "risk", "valuation", "accounting"],
                "Ask AGI": ["decision", "explain_all"],
            },
            "internal": {
                "decision": [
                    "accounting",
                    "business",
                    "industry",
                    "competition",
                    "capital_allocation",
                    "governance",
                    "risk",
                    "economics",
                    "macro",
                    "valuation",
                ],
                "macro": ["economics", "industry"],
                "valuation": ["industry"],
            },
            "not_an_engine": True,
        }

    def analyse_bundle(self, payload: dict[str, Any] | None = None, domains: list[str] | None = None) -> dict[str, Any]:
        p = payload or {}
        selected = domains or [
            "accounting",
            "business",
            "industry",
            "competition",
            "capital_allocation",
            "governance",
            "risk",
            "economics",
            "macro",
            "valuation",
            "forecasting",
            "decision",
        ]
        results = {}
        for d in selected:
            try:
                results[d] = self.analyse(d, p)
            except Exception as exc:
                results[d] = {"error": str(exc), "domain": d}
        return {
            "subject_id": str(p.get("company_symbol") or p.get("symbol") or "UNKNOWN").upper(),
            "domains": selected,
            "results": results,
            "decision": results.get("decision"),
        }


def json_blob(obj: Any) -> str:
    return str(obj).lower()


def get_registry() -> ModelRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry()
    return _REGISTRY
