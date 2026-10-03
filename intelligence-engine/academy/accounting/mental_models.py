"""Reusable investor accounting mental models."""

from __future__ import annotations

from academy.accounting.curriculum import COURSE_TITLE, chapter_meta
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
            model_id="cash_harder_than_earnings",
            name="Cash is harder to manipulate than earnings",
            statement="Accrual earnings can be shaped by estimates; cash conversion is the stronger truth serum.",
            application=["Earnings quality scoring", "Fraud/red-flag screens", "FCF underwriting"],
            related_concepts=["operating_cash_flow", "earnings_quality", "accruals"],
            sources=[_src(5), _src(9)],
        ),
        MentalModel(
            model_id="profit_is_not_cash",
            name="Profit is not cash",
            statement="Net income is an accrual construct; only the cash flow statement and FCF bridge tell funding reality.",
            application=["Never equate EBITDA/NI to cash", "Reconcile every thesis to CFO/FCF"],
            related_concepts=["net_income", "ebitda", "free_cash_flow"],
            sources=[_src(5)],
        ),
        MentalModel(
            model_id="growth_consumes_capital",
            name="Growth consumes capital",
            statement="Higher growth absorbs working capital and capex; earnings can rise while free cash flow falls.",
            application=["FCF forecasts", "Reinvestment rate in DCF", "High-growth quality checks"],
            related_concepts=["working_capital", "free_cash_flow", "roic"],
            sources=[_src(6), _src(5)],
        ),
        MentalModel(
            model_id="working_capital_funds_operations",
            name="Working capital funds operations",
            statement="AR, inventory, and payables are the cash engine room of the operating cycle.",
            application=["CCC tracking", "Seasonality models", "Credit risk"],
            related_concepts=["working_capital", "cash_conversion_cycle", "inventory"],
            sources=[_src(6)],
        ),
        MentalModel(
            model_id="depreciation_is_economic_cost",
            name="Depreciation is an economic cost",
            statement="Even though non-cash, depreciation approximates asset consumption; ignoring it overstates owner earnings.",
            application=["EBITDA scepticism", "Maintenance capex vs D&A", "Capital-intensive sectors"],
            related_concepts=["depreciation", "ebitda", "free_cash_flow"],
            sources=[_src(2), _src(4)],
        ),
        MentalModel(
            model_id="accounting_earnings_ne_economic_value",
            name="Accounting earnings ≠ economic value",
            statement="Book profits and book capital are starting points; investors adjust classifications and estimates toward economics.",
            application=["Lease/R&D/SBC adjustments", "ROIC clean-ups", "Moat vs accounting illusion"],
            related_concepts=["roic", "leases", "capitalised_expenses", "earnings_quality"],
            sources=[_src(8), _src(7)],
        ),
    ]
