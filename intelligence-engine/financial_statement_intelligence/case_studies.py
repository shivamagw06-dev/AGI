"""Case Study Library — Module 13.

Eight companies spanning distinct sector archetypes, each with a
3-period ``FinancialSeries``, run through the FULL Phase 2 stack
(statement intelligence, earnings quality, red flags, health score,
narrative, industry lens) to produce Explain / Interpret / Strengths /
Weaknesses — computed, never hand-labelled.

IMPORTANT: these are ILLUSTRATIVE, DIRECTIONALLY-REALISTIC FIXTURES for
teaching and validating the engine — not live-fetched reported
financials. ``data_source`` is always tagged accordingly, and every
consumer of this module must treat the numbers as synthetic. HDFC
Bank's fixture in particular is a simplified P&L/Balance Sheet mapped
onto Phase 2's generic (non-bank-specific) schema — a real banking
analysis needs deposits/advances/NIM fields this schema does not yet
model; that limitation is called out explicitly in its ``meta``.
"""

from __future__ import annotations

from typing import Any

from financial_statement_intelligence.earnings_quality import assess_earnings_quality
from financial_statement_intelligence.health_score import score_financial_health
from financial_statement_intelligence.industry_lens import industry_context
from financial_statement_intelligence.narrative_generator import generate_narrative
from financial_statement_intelligence.red_flag_detector import detect_red_flags
from financial_statement_intelligence.rule_library import evaluate_rules
from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod
from financial_statement_intelligence.statement_intelligence import overall_direction


def _series(company: str, sector: str, rows: list[dict[str, Any]]) -> FinancialSeries:
    periods = [
        StatementPeriod(label=row.pop("label"), sequence=i + 1, **row)
        for i, row in enumerate(rows)
    ]
    return FinancialSeries(company=company, periods=periods, sector=sector, data_source="illustrative_fixture_not_live")


CASE_STUDIES: dict[str, FinancialSeries] = {
    "apple": _series(
        "Apple Inc. (illustrative)", "consumer_electronics",
        [
            dict(label="FY22", revenue=394000, cogs=223000, opex=51000, depreciation=11000, interest_expense=2900,
                 tax_expense=19300, shares_outstanding=16000, cash=48000, receivables=28000, inventory=4900,
                 ppe_net=42000, payables=64000, short_term_debt=11000, long_term_debt=99000, share_capital=64000,
                 retained_earnings=5600, treasury_stock=3000, operating_cf=122000, capex=10700, dividends_paid=14800,
                 buybacks=89400),
            dict(label="FY23", revenue=383000, cogs=214000, opex=54000, depreciation=11500, interest_expense=3900,
                 tax_expense=16700, shares_outstanding=15550, cash=61500, receivables=29500, inventory=6300,
                 ppe_net=43700, payables=62600, short_term_debt=9800, long_term_debt=95000, share_capital=73800,
                 retained_earnings=-214, treasury_stock=3000, operating_cf=110500, capex=10960, dividends_paid=15000,
                 buybacks=77500),
            dict(label="FY24", revenue=391000, cogs=210000, opex=57000, depreciation=11400, interest_expense=3900,
                 tax_expense=29700, shares_outstanding=15100, cash=65200, receivables=33400, inventory=7300,
                 ppe_net=45700, payables=68900, short_term_debt=10900, long_term_debt=97000, share_capital=83300,
                 retained_earnings=-19100, treasury_stock=3000, operating_cf=118300, capex=9450, dividends_paid=15200,
                 buybacks=95000),
        ],
    ),
    "microsoft": _series(
        "Microsoft Corp. (illustrative)", "software",
        [
            dict(label="FY22", revenue=198000, cogs=62700, opex=52200, depreciation=14400, interest_expense=2100,
                 tax_expense=10980, shares_outstanding=7480, cash=104800, receivables=44300, inventory=3700,
                 ppe_net=74400, payables=19000, short_term_debt=2800, long_term_debt=47000, share_capital=86900,
                 retained_earnings=84300, treasury_stock=0, operating_cf=89000, capex=23900, dividends_paid=18500,
                 buybacks=32700),
            dict(label="FY23", revenue=212000, cogs=65900, opex=57700, depreciation=14700, interest_expense=1970,
                 tax_expense=16950, shares_outstanding=7430, cash=111300, receivables=48700, inventory=2500,
                 ppe_net=95400, payables=18800, short_term_debt=2800, long_term_debt=42700, share_capital=93700,
                 retained_earnings=118800, treasury_stock=0, operating_cf=87600, capex=28100, dividends_paid=19800,
                 buybacks=22200),
            dict(label="FY24", revenue=245100, cogs=74100, opex=61600, depreciation=22300, interest_expense=2350,
                 tax_expense=19700, shares_outstanding=7430, cash=75500, receivables=56900, inventory=1500,
                 ppe_net=135800, payables=21300, short_term_debt=0, long_term_debt=41900, share_capital=100900,
                 retained_earnings=173700, treasury_stock=0, operating_cf=118500, capex=44500, dividends_paid=21800,
                 buybacks=17300),
        ],
    ),
    "reliance": _series(
        "Reliance Industries (illustrative)", "conglomerates",
        [
            dict(label="FY22", revenue=792756, cogs=560000, opex=95000, depreciation=27700, interest_expense=17400,
                 tax_expense=15600, cash=195000, receivables=27300, inventory=76300, ppe_net=511600, payables=140000,
                 short_term_debt=48000, long_term_debt=290000, share_capital=676800, retained_earnings=0,
                 operating_cf=91700, capex=143700, dividends_paid=8300, debt_raised=95000, debt_repaid=40000),
            dict(label="FY23", revenue=974864, cogs=730000, opex=105000, depreciation=42900, interest_expense=22200,
                 tax_expense=17400, cash=185000, receivables=32200, inventory=90800, ppe_net=629200, payables=155000,
                 short_term_debt=55000, long_term_debt=310000, share_capital=676800, retained_earnings=21500,
                 operating_cf=118500, capex=141600, dividends_paid=9100, debt_raised=80000, debt_repaid=45000),
            dict(label="FY24", revenue=900000, cogs=630000, opex=118000, depreciation=57000, interest_expense=21500,
                 tax_expense=19100, cash=175000, receivables=35800, inventory=98600, ppe_net=693500, payables=162000,
                 short_term_debt=52000, long_term_debt=305000, share_capital=676800, retained_earnings=44600,
                 operating_cf=143000, capex=125000, dividends_paid=9800, debt_raised=60000, debt_repaid=65000),
        ],
    ),
    "tcs": _series(
        "Tata Consultancy Services (illustrative)", "it_services",
        [
            dict(label="FY22", revenue=191754, cogs=88500, opex=52700, depreciation=4400, interest_expense=530,
                 tax_expense=10200, shares_outstanding=3660, cash=8500, receivables=42200, inventory=0,
                 ppe_net=17200, payables=13400, short_term_debt=0, long_term_debt=3900, share_capital=9800,
                 retained_earnings=88800, treasury_stock=0, operating_cf=35800, capex=4200, dividends_paid=23500,
                 buybacks=17000),
            dict(label="FY23", revenue=225458, cogs=110800, opex=59200, depreciation=5400, interest_expense=630,
                 tax_expense=11700, shares_outstanding=3660, cash=6800, receivables=48500, inventory=0,
                 ppe_net=17800, payables=15200, short_term_debt=0, long_term_debt=4700, share_capital=9800,
                 retained_earnings=104300, treasury_stock=0, operating_cf=39300, capex=4900, dividends_paid=42000,
                 buybacks=0),
            dict(label="FY24", revenue=240893, cogs=118700, opex=61700, depreciation=5800, interest_expense=620,
                 tax_expense=12300, shares_outstanding=3660, cash=9200, receivables=50100, inventory=0,
                 ppe_net=18400, payables=15900, short_term_debt=0, long_term_debt=4200, share_capital=9800,
                 retained_earnings=121300, treasury_stock=0, operating_cf=44500, capex=5100, dividends_paid=35800,
                 buybacks=0),
        ],
    ),
    "infosys": _series(
        "Infosys (illustrative)", "it_services",
        [
            dict(label="FY22", revenue=121641, cogs=63900, opex=30800, depreciation=3600, interest_expense=280,
                 tax_expense=6900, shares_outstanding=4230, cash=13800, receivables=25400, inventory=0,
                 ppe_net=12200, payables=8300, short_term_debt=0, long_term_debt=1500, share_capital=2100,
                 retained_earnings=58900, treasury_stock=0, operating_cf=23100, capex=2900, dividends_paid=14600,
                 buybacks=9200),
            dict(label="FY23", revenue=146767, cogs=81300, opex=35700, depreciation=4600, interest_expense=350,
                 tax_expense=7600, shares_outstanding=4150, cash=10900, receivables=29100, inventory=0,
                 ppe_net=13800, payables=9600, short_term_debt=0, long_term_debt=1900, share_capital=2100,
                 retained_earnings=65200, treasury_stock=0, operating_cf=24800, capex=3400, dividends_paid=16700,
                 buybacks=0),
            dict(label="FY24", revenue=153670, cogs=85200, opex=37200, depreciation=4900, interest_expense=370,
                 tax_expense=7800, shares_outstanding=4130, cash=12300, receivables=28700, inventory=0,
                 ppe_net=14500, payables=9900, short_term_debt=0, long_term_debt=1700, share_capital=2100,
                 retained_earnings=71600, treasury_stock=0, operating_cf=27600, capex=3100, dividends_paid=17300,
                 buybacks=0),
        ],
    ),
    "hdfcbank": _series(
        "HDFC Bank (illustrative — simplified, not a true bank schema)", "banks",
        [
            dict(label="FY22", revenue=157263, cogs=0, opex=45000, depreciation=2200, interest_expense=52000,
                 tax_expense=9800, cash=203000, receivables=0, inventory=0, ppe_net=8300,
                 payables=1503300, short_term_debt=0, long_term_debt=180000, share_capital=5500,
                 retained_earnings=195000, operating_cf=45000, capex=2000, dividends_paid=0),
            dict(label="FY23", revenue=196000, cogs=0, opex=52000, depreciation=2500, interest_expense=68000,
                 tax_expense=12100, cash=224000, receivables=0, inventory=0, ppe_net=9100,
                 payables=1800000, short_term_debt=0, long_term_debt=210000, share_capital=5500,
                 retained_earnings=239400, operating_cf=52000, capex=2400, dividends_paid=8500),
            dict(label="FY24", revenue=280000, cogs=0, opex=68000, depreciation=3000, interest_expense=118000,
                 tax_expense=17300, cash=246000, receivables=0, inventory=0, ppe_net=10400,
                 payables=2400000, short_term_debt=0, long_term_debt=290000, share_capital=5500,
                 retained_earnings=290600, operating_cf=61000, capex=2800, dividends_paid=8800),
        ],
    ),
    "jsw_energy": _series(
        "JSW Energy (illustrative)", "power",
        [
            dict(label="FY22", revenue=8300, cogs=4500, opex=1200, depreciation=1100, interest_expense=1050,
                 tax_expense=180, cash=1400, receivables=1800, inventory=350, ppe_net=17800, payables=1100,
                 short_term_debt=800, long_term_debt=13500, share_capital=1640, retained_earnings=3100,
                 operating_cf=2400, capex=1900, dividends_paid=250, debt_raised=1500, debt_repaid=900),
            dict(label="FY23", revenue=10700, cogs=6300, opex=1350, depreciation=1250, interest_expense=1180,
                 tax_expense=210, cash=1150, receivables=2200, inventory=420, ppe_net=19600, payables=1300,
                 short_term_debt=900, long_term_debt=15400, share_capital=1640, retained_earnings=3450,
                 operating_cf=2250, capex=3400, dividends_paid=280, debt_raised=3200, debt_repaid=1000),
            dict(label="FY24", revenue=11900, cogs=6900, opex=1500, depreciation=1450, interest_expense=1420,
                 tax_expense=260, cash=980, receivables=2650, inventory=480, ppe_net=23100, payables=1450,
                 short_term_debt=1000, long_term_debt=18200, share_capital=1640, retained_earnings=3780,
                 operating_cf=2050, capex=4600, dividends_paid=300, debt_raised=4000, debt_repaid=1100),
        ],
    ),
    "asian_paints": _series(
        "Asian Paints (illustrative)", "consumer_staples",
        [
            dict(label="FY22", revenue=30190, cogs=18100, opex=6300, depreciation=560, interest_expense=140,
                 tax_expense=1350, shares_outstanding=959, cash=900, receivables=2400, inventory=3900,
                 ppe_net=4900, payables=3800, short_term_debt=100, long_term_debt=300, share_capital=96,
                 retained_earnings=8200, operating_cf=3200, capex=850, dividends_paid=1650, buybacks=0),
            dict(label="FY23", revenue=34840, cogs=20200, opex=7100, depreciation=650, interest_expense=160,
                 tax_expense=1750, shares_outstanding=959, cash=1100, receivables=2650, inventory=4300,
                 ppe_net=5600, payables=4100, short_term_debt=100, long_term_debt=280, share_capital=96,
                 retained_earnings=9450, operating_cf=3900, capex=1100, dividends_paid=2050, buybacks=0),
            dict(label="FY24", revenue=34940, cogs=19400, opex=7700, depreciation=720, interest_expense=150,
                 tax_expense=1780, shares_outstanding=959, cash=1300, receivables=2550, inventory=4150,
                 ppe_net=6300, payables=4000, short_term_debt=80, long_term_debt=260, share_capital=96,
                 retained_earnings=10800, operating_cf=4400, capex=1200, dividends_paid=2200, buybacks=0),
        ],
    ),
}


def list_case_studies() -> list[dict[str, str]]:
    return [
        {"key": key, "company": series.company, "sector": series.sector, "periods": len(series.periods)}
        for key, series in CASE_STUDIES.items()
    ]


def analyse_case_study(key: str) -> dict[str, Any]:
    """Explain / Interpret / Strengths / Weaknesses — all computed, none hand-typed."""
    series = CASE_STUDIES.get(key)
    if not series:
        return {"found": False, "key": key}

    prior, current = series.pair(lag=1)
    findings = evaluate_rules(compute_deltas(prior, current)) if prior and current else []
    strengths = [f.explanation for f in findings if f.severity == "positive"]
    weaknesses = [f.explanation for f in findings if f.severity in ("medium", "high")]

    return {
        "found": True,
        "key": key,
        "company": series.company,
        "sector": series.sector,
        "data_source": series.data_source,
        "periods": [p.label for p in series.periods],
        "overall_direction": overall_direction(series),
        "earnings_quality": assess_earnings_quality(series),
        "red_flags": detect_red_flags(series),
        "financial_health_score": score_financial_health(series),
        "narrative": generate_narrative(series),
        "industry_context": industry_context(series.sector) if series.sector else {"found": False},
        "strengths": strengths,
        "weaknesses": weaknesses,
    }
