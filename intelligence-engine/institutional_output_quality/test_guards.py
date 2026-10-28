from institutional_output_quality.guards import (
    dedupe_research_text,
    filter_company_framework_text,
    has_numeric_valuation_evidence,
    has_supported_financial_evidence,
    has_supported_valuation_evidence,
    requires_full_company_analysis,
)


def test_analyse_resolved_company_requires_full_desk():
    assert requires_full_company_analysis("Analyse Reliance Industries", "RELIANCE")
    assert requires_full_company_analysis("Please review ICICI Bank", "ICICIBANK")
    assert not requires_full_company_analysis("Analyse AI spending", None)
    assert not requires_full_company_analysis("What is Reliance?", "RELIANCE")


def test_repeated_fragments_are_deduplicated():
    text = "Reliance has four engines. Reliance has four engines. Jio monetises connectivity."
    assert dedupe_research_text(text) == (
        "Reliance has four engines. Jio monetises connectivity."
    )


def test_truncated_copy_is_deduplicated_against_complete_sentence():
    text = (
        "Reliance Industries is a multi-engine Indian conglomerate with O2C, Jio and Retail. "
        "Reliance Industries is a multi-engine Indian conglomerate with O2C…"
    )
    assert dedupe_research_text(text) == (
        "Reliance Industries is a multi-engine Indian conglomerate with O2C, Jio and Retail."
    )


def test_reliance_rejects_metals_framework_but_keeps_segment_evidence():
    values = [
        "Industry DNA: metals",
        "Entry barriers: capital, ore linkages.",
        "Jio ARPU and subscriber growth are segment KPIs.",
    ]
    assert filter_company_framework_text(values, "RELIANCE") == [
        "Jio ARPU and subscriber growth are segment KPIs."
    ]


def test_valuation_requires_numeric_market_or_model_evidence():
    assert not has_numeric_valuation_evidence({"label": "Supportive", "score": 76})
    assert has_numeric_valuation_evidence({"multiples": {"ev_ebitda": 12.4}})
    assert has_numeric_valuation_evidence({"sotp": 3100.0})


def test_valuation_label_requires_provenance_and_as_of_date():
    assert not has_supported_valuation_evidence({"ev_ebitda": 12.4})
    assert has_supported_valuation_evidence(
        {"ev_ebitda": 12.4, "as_of": "2026-08-08", "source": "exchange filing"}
    )


def test_financials_require_period_units_and_source():
    assert not has_supported_financial_evidence(
        {"revenue": 119470, "ebitda_margin": 16.0}
    )
    assert has_supported_financial_evidence(
        {
            "revenue": 119470,
            "ebitda_margin": 16.0,
            "fiscal_period": "FY2026",
            "currency": "USD",
            "unit": "million",
            "source": "annual report",
        }
    )
