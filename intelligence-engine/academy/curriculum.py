"""Mankiw Principles of Economics — course map with provenance anchors.

Printed page numbers follow Mankiw 7e Brief Contents.
PDF page ≈ printed_page + 36 for this local scan (validated on Ch4/23/33).
"""

from __future__ import annotations

from typing import Any

from academy.schema import COURSE_EDITION, COURSE_ID, COURSE_TITLE

PDF_PAGE_OFFSET = 36

CHAPTERS: list[dict[str, Any]] = [
    {"chapter": 1, "title": "Ten Principles of Economics", "part": "I Introduction", "printed_page": 3},
    {"chapter": 2, "title": "Thinking Like an Economist", "part": "I Introduction", "printed_page": 19},
    {"chapter": 3, "title": "Interdependence and the Gains from Trade", "part": "I Introduction", "printed_page": 47},
    {"chapter": 4, "title": "The Market Forces of Supply and Demand", "part": "II How Markets Work", "printed_page": 65},
    {"chapter": 5, "title": "Elasticity and Its Application", "part": "II How Markets Work", "printed_page": 89},
    {"chapter": 6, "title": "Supply, Demand, and Government Policies", "part": "II How Markets Work", "printed_page": 111},
    {"chapter": 7, "title": "Consumers, Producers, and the Efficiency of Markets", "part": "III Markets and Welfare", "printed_page": 135},
    {"chapter": 8, "title": "Application: The Costs of Taxation", "part": "III Markets and Welfare", "printed_page": 155},
    {"chapter": 9, "title": "Application: International Trade", "part": "III Markets and Welfare", "printed_page": 171},
    {"chapter": 10, "title": "Externalities", "part": "IV The Economics of the Public Sector", "printed_page": 195},
    {"chapter": 11, "title": "Public Goods and Common Resources", "part": "IV The Economics of the Public Sector", "printed_page": 215},
    {"chapter": 12, "title": "The Design of the Tax System", "part": "IV The Economics of the Public Sector", "printed_page": 233},
    {"chapter": 13, "title": "The Costs of Production", "part": "V Firm Behavior and the Organization of Industry", "printed_page": 259},
    {"chapter": 14, "title": "Firms in Competitive Markets", "part": "V Firm Behavior and the Organization of Industry", "printed_page": 279},
    {"chapter": 15, "title": "Monopoly", "part": "V Firm Behavior and the Organization of Industry", "printed_page": 299},
    {"chapter": 16, "title": "Monopolistic Competition", "part": "V Firm Behavior and the Organization of Industry", "printed_page": 329},
    {"chapter": 17, "title": "Oligopoly", "part": "V Firm Behavior and the Organization of Industry", "printed_page": 347},
    {"chapter": 18, "title": "The Markets for the Factors of Production", "part": "VI The Economics of Labor Markets", "printed_page": 373},
    {"chapter": 19, "title": "Earnings and Discrimination", "part": "VI The Economics of Labor Markets", "printed_page": 395},
    {"chapter": 20, "title": "Income Inequality and Poverty", "part": "VI The Economics of Labor Markets", "printed_page": 413},
    {"chapter": 21, "title": "The Theory of Consumer Choice", "part": "VII Topics for Further Study", "printed_page": 435},
    {"chapter": 22, "title": "Frontiers of Microeconomics", "part": "VII Topics for Further Study", "printed_page": 461},
    {"chapter": 23, "title": "Measuring a Nation’s Income", "part": "VIII The Data of Macroeconomics", "printed_page": 483},
    {"chapter": 24, "title": "Measuring the Cost of Living", "part": "VIII The Data of Macroeconomics", "printed_page": 505},
    {"chapter": 25, "title": "Production and Growth", "part": "IX The Real Economy in the Long Run", "printed_page": 523},
    {"chapter": 26, "title": "Saving, Investment, and the Financial System", "part": "IX The Real Economy in the Long Run", "printed_page": 547},
    {"chapter": 27, "title": "The Basic Tools of Finance", "part": "IX The Real Economy in the Long Run", "printed_page": 569},
    {"chapter": 28, "title": "Unemployment", "part": "IX The Real Economy in the Long Run", "printed_page": 585},
    {"chapter": 29, "title": "The Monetary System", "part": "X Money and Prices in the Long Run", "printed_page": 609},
    {"chapter": 30, "title": "Money Growth and Inflation", "part": "X Money and Prices in the Long Run", "printed_page": 633},
    {"chapter": 31, "title": "Open-Economy Macroeconomics: Basic Concepts", "part": "XI The Macroeconomics of Open Economies", "printed_page": 659},
    {"chapter": 32, "title": "A Macroeconomic Theory of the Open Economy", "part": "XI The Macroeconomics of Open Economies", "printed_page": 683},
    {"chapter": 33, "title": "Aggregate Demand and Aggregate Supply", "part": "XII Short-Run Economic Fluctuations", "printed_page": 707},
    {"chapter": 34, "title": "The Influence of Monetary and Fiscal Policy on Aggregate Demand", "part": "XII Short-Run Economic Fluctuations", "printed_page": 729},
    {"chapter": 35, "title": "The Short-Run Trade-off between Inflation and Unemployment", "part": "XII Short-Run Economic Fluctuations", "printed_page": 757},
    {"chapter": 36, "title": "Six Debates over Macroeconomic Policy", "part": "XIII Final Thoughts", "printed_page": 795},
]

# Canonical concept → primary teaching chapter (curriculum ownership)
CONCEPT_CHAPTER_MAP: dict[str, int] = {
    "opportunity_cost": 1,
    "trade_offs": 1,
    "incentives": 1,
    "marginal_thinking": 1,
    "comparative_advantage": 3,
    "gains_from_trade": 3,
    "supply_and_demand": 4,
    "market_equilibrium": 4,
    "elasticity": 5,
    "price_controls": 6,
    "consumer_producer_surplus": 7,
    "deadweight_loss": 8,
    "international_trade": 9,
    "externalities": 10,
    "public_goods": 11,
    "marginal_cost": 13,
    "competitive_markets": 14,
    "market_power": 15,
    "oligopoly": 17,
    "productivity": 18,
    "gdp": 23,
    "inflation": 24,
    "cpi": 24,
    "economic_growth": 25,
    "saving_and_investment": 26,
    "present_value": 27,
    "risk_and_diversification": 27,
    "unemployment": 28,
    "money_supply": 29,
    "monetary_system": 29,
    "quantity_theory_of_money": 30,
    "exchange_rates": 31,
    "aggregate_demand": 33,
    "aggregate_supply": 33,
    "business_cycle": 33,
    "recession": 33,
    "monetary_policy": 34,
    "fiscal_policy": 34,
    "phillips_curve": 35,
    "stagflation": 33,
    "deflation": 30,
    "liquidity": 29,
    "credit": 26,
    "yield_curve": 27,
    "discount_rate": 27,
    "creative_destruction": 25,
}


def chapter_meta(chapter: int) -> dict[str, Any]:
    for row in CHAPTERS:
        if row["chapter"] == chapter:
            out = dict(row)
            out["pdf_page"] = row["printed_page"] + PDF_PAGE_OFFSET
            out["book"] = COURSE_TITLE
            out["edition"] = COURSE_EDITION
            out["course_id"] = COURSE_ID
            return out
    raise KeyError(f"Unknown chapter {chapter}")


def course_manifest() -> dict[str, Any]:
    return {
        "course_id": COURSE_ID,
        "title": COURSE_TITLE,
        "edition": COURSE_EDITION,
        "author": "N. Gregory Mankiw",
        "mission": "Institutional finance/economics curriculum — understanding, not summarisation",
        "architecture_status": "v1.0.1 LOCKED",
        "chapter_count": len(CHAPTERS),
        "chapters": [chapter_meta(c["chapter"]) for c in CHAPTERS],
        "concept_chapter_map": CONCEPT_CHAPTER_MAP,
        "pdf_page_offset": PDF_PAGE_OFFSET,
        "not_a_summariser": True,
    }
