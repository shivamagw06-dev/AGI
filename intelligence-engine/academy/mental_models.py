"""Reusable mental models extracted for institutional reasoning."""

from __future__ import annotations

from academy.curriculum import chapter_meta
from academy.schema import MentalModel, SourceRef


def _src(chapter: int, section: str | None = None) -> SourceRef:
    meta = chapter_meta(chapter)
    return SourceRef(
        chapter=chapter,
        chapter_title=meta["title"],
        section=section,
        printed_page=meta["printed_page"],
        pdf_page=meta["pdf_page"],
    )


def all_mental_models() -> list[MentalModel]:
    return [
        MentalModel(
            model_id="opportunity_cost",
            name="Opportunity Cost",
            statement="The true cost of any choice is the value of the best alternative forgone.",
            application=[
                "Rank projects by economic profit, not accounting profit alone",
                "Include capital's next-best use in hurdle rates",
            ],
            related_concepts=["opportunity_cost", "present_value", "discount_rate"],
            sources=[_src(1, "1-1a")],
        ),
        MentalModel(
            model_id="marginal_thinking",
            name="Marginal Thinking",
            statement="Optimise by comparing incremental benefits and costs of the next unit of action.",
            application=["Pricing", "Capacity utilisation", "Hiring and inventory"],
            related_concepts=["marginal_thinking", "marginal_cost", "market_equilibrium"],
            sources=[_src(1, "1-1b")],
        ),
        MentalModel(
            model_id="trade_offs",
            name="Trade-offs",
            statement="Every allocation chooses what not to fund; efficiency requires explicit trade-offs.",
            application=["Portfolio construction", "Fiscal choices", "Capex vs buybacks"],
            related_concepts=["trade_offs", "opportunity_cost", "fiscal_policy"],
            sources=[_src(1, "1-1a")],
        ),
        MentalModel(
            model_id="incentives",
            name="Incentives",
            statement="Behaviour follows the payoffs embedded in prices, taxes, contracts, and regulation.",
            application=["Management compensation", "Tax incidence", "Credit underwriting"],
            related_concepts=["incentives", "elasticity", "fiscal_policy"],
            sources=[_src(1, "1-1c")],
        ),
        MentalModel(
            model_id="elasticity",
            name="Elasticity",
            statement="Sensitivity of quantity to price (or income) determines power, tax incidence, and volume risk.",
            application=["Price hikes", "Subsidy design", "Demand forecasting"],
            related_concepts=["elasticity", "market_power", "inflation"],
            sources=[_src(5, "5-1")],
        ),
        MentalModel(
            model_id="market_equilibrium",
            name="Market Equilibrium",
            statement="Prices adjust to clear markets unless frictions or controls prevent clearing.",
            application=["Commodity pricing", "Shortage/surplus diagnosis"],
            related_concepts=["market_equilibrium", "supply_and_demand", "price_controls"],
            sources=[_src(4, "4-4")],
        ),
        MentalModel(
            model_id="comparative_advantage",
            name="Comparative Advantage",
            statement="Specialise where opportunity cost is lowest; trade expands consumption possibilities.",
            application=["Supply-chain location", "Export competitiveness", "Trade policy"],
            related_concepts=["comparative_advantage", "gains_from_trade", "international_trade"],
            sources=[_src(3, "3-2")],
        ),
        MentalModel(
            model_id="creative_destruction",
            name="Creative Destruction",
            statement="Innovation raises living standards by displacing obsolete products, firms, and routines.",
            application=["Disruption risk", "Capex redirection", "Incumbent moat decay"],
            related_concepts=["creative_destruction", "economic_growth", "productivity"],
            sources=[_src(25)],
        ),
        MentalModel(
            model_id="business_cycles",
            name="Business Cycles",
            statement="Activity fluctuates around trend; investment, credit, and unemployment move with recognisable lags.",
            application=["Sector rotation", "Credit-risk timing", "Cyclical vs defensive allocation"],
            related_concepts=["business_cycle", "recession", "unemployment", "credit"],
            sources=[_src(33, "33-1")],
        ),
        MentalModel(
            model_id="network_effects",
            name="Network Effects",
            statement="A product's value rises as more users join, creating demand-side scale and winner-take-most dynamics.",
            application=[
                "Platform and software moats",
                "Telecom subscriber scale",
                "Payment/network businesses",
            ],
            related_concepts=["market_power", "oligopoly", "incentives"],
            sources=[_src(15), _src(22)],
        ),
    ]
