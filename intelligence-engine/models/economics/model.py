"""Economic Intelligence — policy transmission and macro linkages."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id

# Explicit transmission chains (institutional relationships, not ad-hoc prose)
TRANSMISSION_CHAINS = [
    {
        "id": "repo_to_capex",
        "nodes": [
            "repo_rate",
            "bank_lending",
            "housing",
            "construction",
            "cement",
            "steel",
            "power",
            "capital_goods",
            "corporate_earnings",
        ],
    },
    {
        "id": "usd_inr_to_exporters",
        "nodes": ["usd_inr", "exporter_competitiveness", "it_services_margins", "exporter_volumes", "corporate_earnings"],
    },
    {
        "id": "crude_to_inflation",
        "nodes": ["crude_oil", "inflation", "policy_rate_path", "multiples", "corporate_earnings"],
    },
    {
        "id": "credit_growth_cycle",
        "nodes": ["money_supply", "credit_growth", "consumption_capex", "bank_nims_asset_quality", "corporate_earnings"],
    },
]


class EconomicModel(DomainModel):
    """Teach AGI macro variables and explicit policy transmission paths."""

    domain = "economics"
    version = "1.0.0"
    name = "Economic Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p, default="MACRO")
        gdp = num(p, "gdp_growth", 0.065)
        inflation = num(p, "inflation", 0.045)
        repo = num(p, "repo_rate", 0.065)
        liquidity = num(p, "liquidity_score", 0.55)
        credit_growth = num(p, "credit_growth", 0.12)
        fx_vol = num(p, "fx_volatility", 0.3)

        # Macro regime score: growth supportive, inflation contained, liquidity ok
        regime = clamp(
            0.35 * clamp((gdp - 0.04) / 0.05)
            + 0.25 * clamp(1.0 - abs(inflation - 0.04) / 0.04)
            + 0.2 * liquidity
            + 0.2 * clamp(credit_growth / 0.15)
            - 0.1 * fx_vol
        )
        label = "supportive" if regime >= 0.65 else "neutral" if regime >= 0.45 else "restrictive"
        chain_id = str(p.get("transmission_chain") or "repo_to_capex")
        chain = next((c for c in TRANSMISSION_CHAINS if c["id"] == chain_id), TRANSMISSION_CHAINS[0])
        relationships = [
            {"from": chain["nodes"][i], "to": chain["nodes"][i + 1], "type": "transmits_to"}
            for i in range(len(chain["nodes"]) - 1)
        ]
        summary = (
            f"Macro regime {label}. GDP {gdp:.1%}, inflation {inflation:.1%}, repo {repo:.1%}. "
            f"Transmission focus: {' → '.join(chain['nodes'][:5])}…"
        )
        return AnalysisResult(
            object_type="EconomicRegime",
            object_id=new_id("eco"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(regime, 4),
            label=label,
            confidence=0.66,
            summary=summary,
            outputs={
                "regime": label,
                "variables": {
                    "gdp_growth": gdp,
                    "inflation": inflation,
                    "repo_rate": repo,
                    "liquidity_score": liquidity,
                    "credit_growth": credit_growth,
                    "fx_volatility": fx_vol,
                    "yield_curve": p.get("yield_curve"),
                    "money_supply_growth": num(p, "money_supply_growth", 0.1),
                    "commodity_stress": num(p, "commodity_stress", 0.3),
                },
                "transmission_chains": TRANSMISSION_CHAINS,
                "active_chain": chain,
            },
            relationships=relationships,
            explainability={"why": summary, "active_chain": chain, "policy": {"monetary": repo, "fiscal": p.get("fiscal_impulse")}},
        )

    def relationships(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        return {
            "domain": self.domain,
            "chains": TRANSMISSION_CHAINS,
            "active": result.outputs.get("active_chain"),
            "relationships": result.relationships,
        }
