"""Industry Economics — configuration-driven industry models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, subject_id
from models.objects import IndustryModel

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

# Symbol → industry inheritance (configuration, not hard business logic in engines)
SYMBOL_INDUSTRY = {
    "INFY": "it_services",
    "TCS": "it_services",
    "WIPRO": "it_services",
    "HCLTECH": "it_services",
    "HDFCBANK": "banking",
    "ICICIBANK": "banking",
    "SBIN": "banking",
    "RELIANCE": "chemicals",
    "TATAMOTORS": "automobile",
    "MARUTI": "automobile",
    "NTPC": "power",
    "POWERGRID": "utilities",
    "TATASTEEL": "steel",
    "JSWSTEEL": "steel",
    "ULTRACEMCO": "cement",
    "BHARTIARTL": "telecom",
    "SUNPHARMA": "healthcare",
    "DMART": "retail",
    "HDFCLIFE": "insurance",
    "LT": "infrastructure",
}


def load_industry_config(industry_id: str) -> dict[str, Any]:
    path = CONFIG_DIR / f"{industry_id}.json"
    if not path.exists():
        return {
            "industry_id": industry_id,
            "name": industry_id.replace("_", " ").title(),
            "demand_drivers": [],
            "supply_drivers": [],
            "important_kpis": [],
            "typical_risks": [],
            "preferred_valuation_models": ["dcf_fcff", "relative_pe"],
            "capital_intensity": "medium",
            "industry_structure": "unspecified",
            "historical_cycles": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def list_industries() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def resolve_industry(payload: dict[str, Any]) -> str:
    if payload.get("industry_id"):
        return str(payload["industry_id"]).lower()
    if payload.get("industry"):
        return str(payload["industry"]).lower().replace(" ", "_")
    sym = subject_id(payload)
    return SYMBOL_INDUSTRY.get(sym, "it_services")


class IndustryEconomicsModel(DomainModel):
    """Every company inherits a structured, configuration-driven industry model."""

    domain = "industry"
    version = "1.0.0"
    name = "Industry Economics"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        industry_id = resolve_industry(p)
        cfg = load_industry_config(industry_id)
        obj = IndustryModel(
            industry_id=cfg.get("industry_id", industry_id),
            name=cfg.get("name", industry_id),
            demand_drivers=list(cfg.get("demand_drivers") or []),
            supply_drivers=list(cfg.get("supply_drivers") or []),
            kpis=list(cfg.get("important_kpis") or []),
            typical_risks=list(cfg.get("typical_risks") or []),
            preferred_valuation_models=list(cfg.get("preferred_valuation_models") or []),
            capital_intensity=str(cfg.get("capital_intensity") or "medium"),
            industry_structure=str(cfg.get("industry_structure") or ""),
            historical_cycles=list(cfg.get("historical_cycles") or []),
            version=self.version,
        )
        # Coverage/quality score: richer configs score higher
        richness = (
            len(obj.demand_drivers)
            + len(obj.supply_drivers)
            + len(obj.kpis)
            + len(obj.preferred_valuation_models)
        )
        score = clamp(richness / 20.0)
        summary = (
            f"{sid} inherits {obj.name} industry model. "
            f"Preferred valuation: {', '.join(obj.preferred_valuation_models[:3]) or 'n/a'}."
        )
        return AnalysisResult(
            object_type="IndustryModel",
            object_id=new_id("ind"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(score, 4),
            label=obj.industry_id,
            confidence=0.85 if (CONFIG_DIR / f"{industry_id}.json").exists() else 0.45,
            summary=summary,
            outputs={
                "industry": obj.to_dict(),
                "config": cfg,
                "inherited_from_symbol_map": sid in SYMBOL_INDUSTRY,
            },
            red_flags=list(obj.typical_risks[:3]),
            strengths=list(obj.demand_drivers[:3]),
            relationships=[
                {"from": sid, "to": obj.industry_id, "type": "inherits_industry_model"},
                *[
                    {"from": obj.industry_id, "to": d, "type": "demand_driver"}
                    for d in obj.demand_drivers[:6]
                ],
            ],
            explainability={
                "why": summary,
                "kpis": obj.kpis,
                "capital_cycle": cfg.get("capital_cycle"),
                "business_characteristics": cfg.get("business_characteristics"),
            },
        )

    def search(self, query: str, *, limit: int = 20, **kwargs: Any) -> dict[str, Any]:
        q = (query or "").lower()
        hits = []
        for ind in list_industries():
            cfg = load_industry_config(ind)
            blob = json.dumps(cfg).lower()
            if not q or q in ind or q in blob:
                hits.append(
                    {
                        "industry_id": ind,
                        "name": cfg.get("name"),
                        "preferred_valuation_models": cfg.get("preferred_valuation_models"),
                    }
                )
        return {"domain": self.domain, "query": query, "hits": hits[:limit]}
