"""Reusable corporate-finance mental models."""

from __future__ import annotations

from academy.corporate_finance.curriculum import COURSE_TITLE, chapter_meta
from academy.schema import MentalModel, SourceRef


def _src(chapter: int, section: str | None = None) -> SourceRef:
    meta = chapter_meta(chapter)
    return SourceRef(
        book=COURSE_TITLE,
        edition=meta["edition"],
        chapter=chapter,
        chapter_title=meta["title"],
        section=section,
        printed_page=meta.get("printed_page"),
        pdf_page=meta.get("pdf_page"),
    )


def all_mental_models() -> list[MentalModel]:
    return [
        MentalModel(
            model_id="every_rupee_above_cost",
            name="Every ₹1 invested should earn above its cost of capital",
            statement="Accept investments only when expected returns clear a risk-appropriate hurdle.",
            application=["NPV gates", "Capex underwriting", "ROIC vs WACC monitoring"],
            related_concepts=["investment_principle", "hurdle_rate", "npv", "roic_wacc_spread"],
            sources=[_src(1), _src(5)],
        ),
        MentalModel(
            model_id="growth_without_returns_destroys",
            name="Growth without returns destroys value",
            statement="Expanding a negative-spread business makes shareholders poorer.",
            application=["Reject low-ROIC growth", "Haircut empire-building M&A", "Lifecycle payout shift"],
            related_concepts=["incremental_roic", "value_destruction", "organic_reinvestment"],
            sources=[_src(5), _src(12)],
        ),
        MentalModel(
            model_id="debt_amplifies",
            name="Debt amplifies both upside and downside",
            statement="Leverage magnifies equity outcomes and raises distress probability.",
            application=["Optimal structure", "Cyclical industries", "Coverage monitoring"],
            related_concepts=["financial_leverage", "financial_distress", "optimal_capital_structure"],
            sources=[_src(7), _src(8)],
        ),
        MentalModel(
            model_id="cash_strategic_if_allocated",
            name="Cash is a strategic asset only if allocated well",
            statement="Idle or poorly deployed cash is an agency and opportunity-cost problem.",
            application=["Capital allocation scorecards", "Payout vs reinvestment", "M&A discipline"],
            related_concepts=["capital_allocation", "dividend_principle", "agency_costs"],
            sources=[_src(1), _src(11)],
        ),
        MentalModel(
            model_id="buybacks_below_intrinsic",
            name="Buybacks create value only below intrinsic value",
            statement="Repurchases at a premium to intrinsic value transfer wealth to exiting holders.",
            application=["Buyback underwriting", "Reject EPS-only justifications"],
            related_concepts=["share_buybacks", "eps_illusion", "value_creation"],
            sources=[_src(11)],
        ),
        MentalModel(
            model_id="dividends_are_allocation",
            name="Dividends are a capital allocation decision, not evidence of quality",
            statement="Payout quality depends on opportunity set and incremental returns — not the dividend itself.",
            application=["Mature vs growth payout policy", "Avoid dividend = moat fallacy"],
            related_concepts=["dividend_policy", "dividend_principle", "retention_ratio"],
            sources=[_src(10)],
        ),
    ]
