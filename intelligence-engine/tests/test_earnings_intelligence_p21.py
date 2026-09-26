"""P2.1 Financial Statements & Earnings Intelligence — NSE IND-AS XBRL."""

from __future__ import annotations

from company_analysis.financial import analyse_financials
from decision_engine.readiness_gate import compute_coverage_board
from earnings_intelligence.enrich import merge_financials_into_dossier
from earnings_intelligence.production import analyse, health, package_for_ask_agi
from earnings_intelligence.schema import IC10_UNIVERSE, WORKSTREAM_ID
from earnings_intelligence.xbrl import enrich_filing_with_xbrl, parse_financial_xbrl
from phase2_investment_intelligence.contract import validate_engine_payload
from phase2_investment_intelligence.workstreams import WORKSTREAMS


def _corp_q(to_date: str, *, cons: str = "Consolidated", xbrl: str = "https://example.test/q.xml") -> dict:
    return {
        "toDate": to_date,
        "fromDate": to_date,
        "period": "Quarterly",
        "relatingTo": "Quarter",
        "consolidated": cons,
        "audited": "Audited",
        "indAs": "Ind-AS New",
        "xbrl": xbrl,
        "filingDate": to_date,
        "broadCastDate": to_date + " 10:00:00",
        "financialYear": "FY",
        "symbol": "TCS",
        "companyName": "TCS",
        "isin": "INE467B01029",
    }


def _corp_a(to_date: str, *, xbrl: str = "https://example.test/a.xml") -> dict:
    return {
        "toDate": to_date,
        "fromDate": to_date,
        "period": "Annual",
        "relatingTo": "Annual",
        "consolidated": "Consolidated",
        "audited": "Audited",
        "indAs": "Ind-AS New",
        "xbrl": xbrl,
        "filingDate": to_date,
        "broadCastDate": to_date + " 10:00:00",
        "financialYear": "FY",
        "symbol": "TCS",
        "companyName": "TCS",
        "isin": "INE467B01029",
    }


def _unit_ref(tag: str) -> str:
    if "Earnings" in tag or tag == "FaceValueOfEquityShareCapital":
        return "INRPerShare"
    return "INR"


def _income_xbrl(*, revenue: float, pat: float, eps: float = 10.0, ytd_revenue: float | None = None) -> str:
    ytd_revenue = ytd_revenue if ytd_revenue is not None else revenue * 3
    facts = [
        ("OneD", "RevenueFromOperations", revenue),
        ("OneD", "OtherIncome", 1e9),
        ("OneD", "Income", revenue + 1e9),
        ("OneD", "FinanceCosts", 5e8),
        ("OneD", "DepreciationDepletionAndAmortisationExpense", 2e9),
        ("OneD", "ProfitBeforeTax", pat * 1.3),
        ("OneD", "TaxExpense", pat * 0.3),
        ("OneD", "ProfitLossForPeriod", pat),
        ("OneD", "ProfitOrLossAttributableToOwnersOfParent", pat),
        ("OneD", "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations", eps),
        ("OneD", "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations", eps),
        ("FourD", "RevenueFromOperations", ytd_revenue),
        ("FourD", "ProfitLossForPeriod", pat * 3),
    ]
    body = "".join(
        f'<in-bse-fin:{tag} contextRef="{ctx}" '
        f'unitRef="{_unit_ref(tag)}" decimals="2">'
        f'{val:.2f}</in-bse-fin:{tag}>'
        for ctx, tag, val in facts
    )
    seg = (
        '<in-bse-fin:DescriptionOfReportableSegment contextRef="Seg1">Banking</in-bse-fin:DescriptionOfReportableSegment>'
        '<in-bse-fin:SegmentRevenue contextRef="Seg1" unitRef="INR" decimals="2">1000000000.00</in-bse-fin:SegmentRevenue>'
        '<xbrli:context id="Seg1"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity>'
        "<xbrli:period><xbrli:instant>2026-06-30</xbrli:instant></xbrli:period></xbrli:context>"
    )
    return (
        '<?xml version="1.0"?>'
        '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:in-bse-fin="http://www.bseindia.com/xbrl/fin" '
        'xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
        '<xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="INRPerShare"><xbrli:divide><xbrli:unitNumerator>'
        '<xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unitNumerator>'
        '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
        '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>'
        '<xbrli:context id="OneD"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity>'
        "<xbrli:period><xbrli:endDate>2026-06-30</xbrli:endDate></xbrli:period></xbrli:context>"
        '<xbrli:context id="FourD"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity>'
        "<xbrli:period><xbrli:endDate>2026-06-30</xbrli:endDate></xbrli:period></xbrli:context>"
        f"{body}{seg}</xbrli:xbrl>"
    )


def _annual_xbrl(*, revenue: float, pat: float, assets: float, equity: float, ocf: float) -> str:
    # Mirror live NSE shape: P&L on OneD, BS on OneI, annual CF on FourD
    facts = [
        ("OneD", "RevenueFromOperations", revenue),
        ("OneD", "ProfitBeforeTax", pat * 1.3),
        ("OneD", "ProfitLossForPeriod", pat),
        ("OneD", "ProfitOrLossAttributableToOwnersOfParent", pat),
        ("OneD", "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations", 40.0),
        ("OneD", "FinanceCosts", 1e9),
        ("OneD", "DepreciationDepletionAndAmortisationExpense", 5e9),
        ("OneI", "Assets", assets),
        ("OneI", "CurrentAssets", assets * 0.4),
        ("OneI", "CurrentLiabilities", assets * 0.2),
        ("OneI", "CashAndCashEquivalents", assets * 0.1),
        ("OneI", "Equity", equity),
        ("OneI", "EquityShareCapital", equity * 0.1),
        ("OneI", "FaceValueOfEquityShareCapital", 10.0),
        ("OneI", "EquityAttributableToOwnersOfParent", equity),
        ("FourD", "CashFlowsFromUsedInOperatingActivities", ocf),
        ("FourD", "CashFlowsFromUsedInInvestingActivities", -ocf * 0.4),
        ("FourD", "CashFlowsFromUsedInFinancingActivities", -ocf * 0.2),
        ("FourD", "RevenueFromOperations", revenue),
        ("FourD", "ProfitLossForPeriod", pat),
    ]
    body = "".join(
        f'<in-bse-fin:{tag} contextRef="{ctx}" '
        f'unitRef="{_unit_ref(tag)}" decimals="2">'
        f'{val:.2f}</in-bse-fin:{tag}>'
        for ctx, tag, val in facts
    )
    return (
        '<?xml version="1.0"?>'
        '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:in-bse-fin="http://www.bseindia.com/xbrl/fin" '
        'xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
        '<xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="INRPerShare"><xbrli:divide><xbrli:unitNumerator>'
        '<xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unitNumerator>'
        '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
        '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>'
        '<xbrli:context id="OneD"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity>'
        "<xbrli:period><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>"
        '<xbrli:context id="OneI"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity>'
        "<xbrli:period><xbrli:instant>2026-03-31</xbrli:instant></xbrli:period></xbrli:context>"
        '<xbrli:context id="FourD"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity>'
        "<xbrli:period><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>"
        f"{body}</xbrli:xbrl>"
    )


def test_xbrl_income_balance_cashflow_and_segments():
    q = parse_financial_xbrl(_income_xbrl(revenue=6.3e11, pat=1.2e11))
    assert q["ok"] is True
    assert q["has_income"] is True
    assert q["income_statement"]["revenue_from_operations"] == 6.3e5
    assert q["income_statement"]["eps_basic"] == 10.0
    assert q["units_in"] == "inr_million"
    assert q["unit_resolution"]["decimals_used_as_scale"] is False
    assert q["income_statement"]["ebitda"] is not None
    assert q["has_segments"] is True
    a = parse_financial_xbrl(_annual_xbrl(revenue=2.4e12, pat=4.6e11, assets=1e12, equity=8e11, ocf=5e11))
    assert a["has_balance"] is True
    assert a["has_cash_flow"] is True
    assert a["balance_sheet"]["face_value"] == 10.0
    assert a["balance_sheet"]["shares_outstanding"] == 8_000_000_000.0
    assert a["cash_flow"]["free_cash_flow"] is not None


def test_per_share_fact_requires_declared_inr_per_share_unit():
    raw = _income_xbrl(revenue=6.3e11, pat=1.2e11).replace(
        'unitRef="INRPerShare"',
        'unitRef="INR"',
    )
    parsed = parse_financial_xbrl(raw)
    assert parsed["income_statement"]["eps_basic"] is None
    assert parsed["unit_resolution"]["rejected_per_share_facts"] >= 1


def test_integrated_summary_without_a_declared_unit_is_not_guessed():
    filing = {"raw_summary": {"income": "100"}}
    out = enrich_filing_with_xbrl(
        filing,
        injected_xbrl="<xbrli:xbrl></xbrli:xbrl>",
    )
    assert out["integrated_summary_skipped"] == "unit_not_declared"
    assert out["statements"]["income_statement"].get("revenue_from_operations") is None


def test_integrated_summary_lakhs_is_used_only_when_declared():
    filing = {"raw_summary": {"income": "100", "unit": "lakh"}}
    out = enrich_filing_with_xbrl(
        filing,
        injected_xbrl="<xbrli:xbrl></xbrli:xbrl>",
    )
    assert out["statements"]["income_statement"]["revenue_from_operations"] == 10.0
    assert out["units_in"] == "inr_million"
    assert out["scaled_from_integrated_lakhs"] is True


def test_analyse_injected_pack_ttm_and_contract():
    q_urls = [f"https://example.test/q{i}.xml" for i in range(4)]
    a_url = "https://example.test/a.xml"
    quarters = [
        _corp_q("30-Jun-2026", xbrl=q_urls[0]),
        _corp_q("31-Mar-2026", xbrl=q_urls[1]),
        _corp_q("31-Dec-2025", xbrl=q_urls[2]),
        _corp_q("30-Sep-2025", xbrl=q_urls[3]),
        _corp_q("30-Jun-2025", xbrl="https://example.test/q4yoy.xml"),
    ]
    annuals = [
        _corp_a("31-Mar-2026", xbrl=a_url),
        _corp_a("31-Mar-2025", xbrl="https://example.test/a2.xml"),
    ]
    xmap = {
        q_urls[0]: _income_xbrl(revenue=100, pat=20, eps=2),
        q_urls[1]: _income_xbrl(revenue=90, pat=18, eps=1.8),
        q_urls[2]: _income_xbrl(revenue=85, pat=16, eps=1.6),
        q_urls[3]: _income_xbrl(revenue=80, pat=15, eps=1.5),
        "https://example.test/q4yoy.xml": _income_xbrl(revenue=70, pat=12, eps=1.2),
        a_url: _annual_xbrl(revenue=400, pat=80, assets=1000, equity=600, ocf=90),
        "https://example.test/a2.xml": _annual_xbrl(revenue=350, pat=70, assets=900, equity=550, ocf=70),
    }
    pack = analyse(
        "TCS",
        injected_integrated=[],
        injected_quarterly=quarters,
        injected_annual=annuals,
        injected_xbrl_by_url=xmap,
        persist=False,
        quarterly_xbrl=5,
        annual_xbrl=2,
    )
    assert pack["ok"] is True
    assert pack["missing"] is False
    assert pack["coverage_pct"] >= 80
    assert pack["income_available"] is True
    assert pack["ttm_available"] is True
    assert pack["historical_quarters_indexed"] == 5
    assert pack["historical_annuals_indexed"] == 2
    assert pack["balance_sheet_available"] is True
    assert pack["cash_flow_available"] is True
    assert pack["intelligence"]["observations"]
    assert "buy" not in " ".join(pack["intelligence"]["observations"]).lower()
    v = validate_engine_payload(pack)
    assert v["ok"] is True, v


def test_cid_merge_raises_financial_coverage_for_ca_and_gate():
    q_url = "https://example.test/q.xml"
    a_url = "https://example.test/a.xml"
    pack = analyse(
        "TCS",
        injected_integrated=[],
        injected_quarterly=[
            _corp_q("30-Jun-2026", xbrl=q_url),
            _corp_q("31-Mar-2026", xbrl=q_url),
            _corp_q("31-Dec-2025", xbrl=q_url),
            _corp_q("30-Sep-2025", xbrl=q_url),
        ],
        injected_annual=[_corp_a("31-Mar-2026", xbrl=a_url)],
        injected_xbrl_by_url={
            q_url: _income_xbrl(revenue=1e11, pat=2e10),
            a_url: _annual_xbrl(revenue=4e11, pat=8e10, assets=1e12, equity=7e11, ocf=9e10),
        },
        persist=False,
        quarterly_xbrl=4,
        annual_xbrl=1,
    )
    dossier = merge_financials_into_dossier({"ticker": "TCS"}, pack)
    assert dossier["financial_statements"]["income_statement"]["quarterly"]
    assert dossier["financials"]["revenue"] is not None
    assert float(dossier["financials"]["coverage_pct"]) >= 80

    fin = analyse_financials(identity={"sector": "IT"}, cid=dossier)
    assert fin["coverage_pct"] >= 60

    board = compute_coverage_board(
        layers={},
        cid=dossier,
        company_analysis={"financial_intelligence": fin},
    )
    assert float((board.get("dimensions") or {}).get("financials") or 0) >= 60


def test_workstream_implemented_and_health():
    row = next(w for w in WORKSTREAMS if w["id"] == "P2.1")
    assert row["status"] == "implemented"
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["engine"] == "earnings_intelligence"


def test_package_degrades_without_ticker():
    pack = package_for_ask_agi("show financials")
    assert pack.get("skipped") is True


def test_ic10_constant():
    assert len(IC10_UNIVERSE) == 10
