from institutional_orchestrator.response_builder import _comparison_answer


def test_decade_comparison_renders_profit_growth_and_balance_sheet():
    company = {
        "symbol": "TESTBANK",
        "sources": ["Capital IQ workbook"],
        "as_of": "2026-08-07",
        "annual_history": [
            {
                "fiscal_year": "FY2016", "pat": 1000, "equity": 5000,
                "assets": 20000, "debt": 2000, "statement_version": "capiq_workbook_2016",
                "_meta": {"unit_method": "assumed_canonical"},
            },
            {
                "fiscal_year": "FY2026", "pat": 2000, "equity": 9000,
                "assets": 40000, "debt": 3000, "statement_version": "capiq_workbook_2026",
                "_meta": {"unit_method": "assumed_canonical"},
            },
        ],
    }
    answer = _comparison_answer(
        {"ComparisonEvidence": {"payload": {"available": True, "companies": [company]}}},
        question="Compare on 10-year profit growth and balance-sheet quality",
    )
    assert "FY2016" in answer
    assert "FY2026" in answer
    assert "PAT CAGR 7.2%" in answer
    assert "debt/equity 0.33x" in answer
    assert "Capital IQ workbook" in answer
